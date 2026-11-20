"""Evidence gate: refuse before calling the LLM when the best evidence is too weak."""

from __future__ import annotations

from typing import Any


def passes_evidence_gate(results: list[dict[str, Any]], min_rerank_score: float) -> bool:
    """True when the top reranked candidate clears the threshold.

    Records without a ``rerank_score`` (e.g. injected test retrievers or a
    disabled reranker) are not gated, so the threshold never silently blocks
    a pipeline that cannot produce the score.
    """
    if not results:
        return False
    if min_rerank_score <= 0:
        return True
    score = results[0].get("rerank_score")
    if score is None:
        return True
    try:
        return float(score) >= min_rerank_score
    except (TypeError, ValueError):
        return True
