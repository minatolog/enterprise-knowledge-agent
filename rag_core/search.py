"""Hybrid retrieval: dense + BM25 → reciprocal-rank fusion → cross-encoder rerank."""

from __future__ import annotations

import heapq
import re
import threading
from collections.abc import Callable, Iterable
from typing import Any

from rag_core.chunking import search_text
from rag_core.textnorm import normalize

Record = dict[str, Any]
_TOKEN = re.compile(r"[\w㐀-鿿]", re.UNICODE)
RRF_K = 60


def tokenize(text: str) -> list[str]:
    import jieba

    return [token for token in jieba.lcut(normalize(text)) if _TOKEN.search(token)]


class BM25Index:
    """BM25 built once over a fixed record set; ACL filtering happens at query time."""

    def __init__(self, records: Iterable[Record]):
        from rank_bm25 import BM25Okapi

        self.records = list(records)
        if not self.records:
            raise ValueError("BM25 索引没有任何记录")
        self._bm25 = BM25Okapi([tokenize(search_text(record)) for record in self.records])

    def __len__(self) -> int:
        return len(self.records)

    def search(
        self,
        question: str,
        k: int,
        allowed: Callable[[Record], bool] | None = None,
    ) -> list[Record]:
        scores = self._bm25.get_scores(tokenize(question))
        positions = (
            index for index, record in enumerate(self.records)
            if allowed is None or allowed(record)
        )
        best = heapq.nlargest(k, positions, key=scores.__getitem__)
        return [dict(self.records[i], bm25_score=float(scores[i])) for i in best if scores[i] > 0]


def reciprocal_rank_fusion(*ranked_lists: list[Record], rrf_k: int = RRF_K) -> list[Record]:
    scores: dict[str, float] = {}
    merged: dict[str, Record] = {}
    for results in ranked_lists:
        for rank, item in enumerate(results, start=1):
            chunk_id = item["chunk_id"]
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
            merged.setdefault(chunk_id, {}).update(item)
    ordered = sorted(scores, key=scores.__getitem__, reverse=True)
    return [dict(merged[chunk_id], rrf_score=scores[chunk_id]) for chunk_id in ordered]


class Reranker:
    """Lazy CrossEncoder; scores (question, title+section+body) pairs in one batch."""

    def __init__(self, model_name: str, model: Any = None):
        self.model_name = model_name
        self._model = model
        self._lock = threading.Lock()

    def _get(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from sentence_transformers import CrossEncoder

                    self._model = CrossEncoder(self.model_name)
        return self._model

    def rerank(self, question: str, candidates: list[Record]) -> list[Record]:
        if not candidates:
            return []
        query = normalize(question)
        scores = self._get().predict([(query, search_text(item)) for item in candidates])
        ranked = [dict(item, rerank_score=float(score)) for item, score in zip(candidates, scores)]
        return sorted(ranked, key=lambda item: item["rerank_score"], reverse=True)


def hybrid_search(
    question: str,
    *,
    dense: Callable[[str, int], list[Record]],
    sparse: Callable[[str, int], list[Record]],
    reranker: Reranker | None,
    k: int,
    candidate_k: int,
) -> list[Record]:
    """Each branch returns ``candidate_k``; the top ``candidate_k`` fused records are reranked."""
    budget = max(candidate_k, k)
    fused = reciprocal_rank_fusion(dense(question, budget), sparse(question, budget))[:budget]
    if reranker is not None:
        fused = reranker.rerank(question, fused)
    return fused[:k]
