"""BM25, RRF and reranking over the same indexed CNOOC chunks."""

from collections import defaultdict

import jieba
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

from knowledge_config import RERANKER_MODEL
from retrieval import get_collection, retrieve_top_k

_corpus = None
_bm25 = None
_reranker = None


def get_bm25_corpus():
    global _corpus, _bm25
    if _corpus is None:
        records = get_collection().get(include=["documents", "metadatas"])
        _corpus = []
        for chunk_id, text, metadata in sorted(zip(
            records["ids"], records["documents"], records["metadatas"]
        )):
            _corpus.append({
                "chunk_id": chunk_id,
                "text": text,
                "source": metadata["source"],
                "relative_path": metadata["relative_path"],
                "knowledge_base": metadata["knowledge_base"],
                "page_start": metadata["page_start"],
                "page_end": metadata["page_end"],
                "section": metadata["section"],
                "source_url": metadata["source_url"],
            })
        if not _corpus:
            raise RuntimeError("CNOOC Collection 为空，请先运行 index_documents.py")
        _bm25 = BM25Okapi([list(jieba.cut(item["text"])) for item in _corpus])
    return _corpus, _bm25


def retrieve_bm25(question: str, k: int = 5) -> list[dict]:
    corpus, bm25 = get_bm25_corpus()
    scores = bm25.get_scores(list(jieba.cut(question)))
    ranked = sorted(range(len(corpus)), key=lambda i: scores[i], reverse=True)
    return [dict(corpus[i], bm25_score=float(scores[i])) for i in ranked[:k]]


def retrieve_hybrid(question: str, k: int = 3) -> list[dict]:
    candidate_k = max(10, k)
    vector_results = retrieve_top_k(question, k=candidate_k)
    keyword_results = retrieve_bm25(question, k=candidate_k)
    rrf_scores = defaultdict(float)
    candidates = {}
    for results in (vector_results, keyword_results):
        for rank, item in enumerate(results, start=1):
            chunk_id = item["chunk_id"]
            rrf_scores[chunk_id] += 1 / (60 + rank)
            candidates.setdefault(chunk_id, {}).update(item)
    ranked = sorted(rrf_scores, key=lambda chunk_id: rrf_scores[chunk_id], reverse=True)
    return [dict(candidates[chunk_id], rrf_score=rrf_scores[chunk_id]) for chunk_id in ranked[:k]]


def retrieve_with_reranker(question: str, k: int = 3, candidate_k: int = 5) -> list[dict]:
    global _reranker
    candidates = retrieve_hybrid(question, k=candidate_k)
    if not candidates:
        return []
    if _reranker is None:
        _reranker = CrossEncoder(RERANKER_MODEL)
    scores = _reranker.predict([(question, item["text"]) for item in candidates])
    for item, score in zip(candidates, scores):
        item["rerank_score"] = float(score)
    return sorted(candidates, key=lambda item: item["rerank_score"], reverse=True)[:k]
