"""Local P0 retrieval over the CNOOC collection, built on ``rag_core``.

The BM25 index is cached per collection *version*: a re-index (different
chunk count or index-state file) rebuilds it automatically instead of serving
stale chunks until the process restarts.
"""

from __future__ import annotations

import threading

from knowledge_config import DEFAULT_CANDIDATE_K, RERANKER_MODEL, STATE_FILE
from rag_core.search import BM25Index, Reranker, hybrid_search
from retrieval import get_collection, record_from, retrieve_top_k

_lock = threading.Lock()
_bm25: BM25Index | None = None
_bm25_version: tuple | None = None
_reranker = Reranker(RERANKER_MODEL)


def _collection_version(collection) -> tuple:
    try:
        state_mtime = STATE_FILE.stat().st_mtime_ns
    except OSError:
        state_mtime = 0
    return (collection.name, collection.count(), state_mtime)


def get_bm25_index() -> BM25Index:
    global _bm25, _bm25_version
    collection = get_collection()
    version = _collection_version(collection)
    with _lock:
        if _bm25 is None or _bm25_version != version:
            records = collection.get(include=["documents", "metadatas"])
            corpus = [
                record_from(chunk_id, text, metadata)
                for chunk_id, text, metadata in sorted(zip(
                    records["ids"], records["documents"], records["metadatas"]
                ))
            ]
            if not corpus:
                raise RuntimeError("CNOOC Collection 为空，请先运行 index_documents.py")
            _bm25, _bm25_version = BM25Index(corpus), version
        return _bm25


def reset_cache() -> None:
    global _bm25, _bm25_version
    with _lock:
        _bm25, _bm25_version = None, None


def retrieve_bm25(question: str, k: int = 5) -> list[dict]:
    return get_bm25_index().search(question, k)


def retrieve_hybrid(question: str, k: int = 3, candidate_k: int | None = None) -> list[dict]:
    return hybrid_search(
        question,
        dense=lambda q, n: retrieve_top_k(q, k=n),
        sparse=retrieve_bm25,
        reranker=None,
        k=k,
        candidate_k=candidate_k or max(DEFAULT_CANDIDATE_K, k),
    )


def retrieve_with_reranker(question: str, k: int = 3, candidate_k: int = DEFAULT_CANDIDATE_K) -> list[dict]:
    return hybrid_search(
        question,
        dense=lambda q, n: retrieve_top_k(q, k=n),
        sparse=retrieve_bm25,
        reranker=_reranker,
        k=k,
        candidate_k=max(candidate_k, k),
    )
