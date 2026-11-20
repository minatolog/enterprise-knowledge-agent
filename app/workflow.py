"""Request-local LangGraph workflow, shared by CLI and FastAPI."""

from __future__ import annotations

from typing import Any, Callable, TYPE_CHECKING, TypedDict

from langgraph.graph import END, START, StateGraph

from schemas import SourceItem

if TYPE_CHECKING:
    from app.service import RAGResult, RAGService
else:
    # StateGraph resolves annotations at runtime; importing service would cycle.
    RAGResult = Any


class RAGState(TypedDict, total=False):
    question: str
    history: list[dict[str, str]]
    search_query: str
    top_k: int
    candidate_k: int
    request_id: str
    on_retrieval: Callable[[list[dict[str, Any]]], None] | None
    total_start: float
    timings: dict[str, float]
    results: list[dict[str, Any]]
    refusal_reason: str | None
    context: str
    source_by_number: dict[int, SourceItem]
    legacy_source_by_number: dict[int, str]
    answer: str
    result: RAGResult


def route_after_retrieval(state: RAGState) -> str:
    return "empty" if state.get("refusal_reason") else "evidence"


def build_rag_graph(service: RAGService):
    graph = StateGraph(RAGState)
    graph.add_node("check_index", service._check_index)
    graph.add_node("rewrite", service._rewrite)
    graph.add_node("retrieve", service._retrieve)
    graph.add_node("build_context", service._build_context)
    graph.add_node("generate", service._generate)
    graph.add_node("map_citations", service._map_citations)
    graph.add_node("no_evidence", service._no_evidence)
    graph.add_edge(START, "check_index")
    graph.add_edge("check_index", "rewrite")
    graph.add_edge("rewrite", "retrieve")
    # The evidence gate (empty results or a top rerank score under
    # RAG_MIN_RERANK_SCORE) refuses before any LLM call.
    graph.add_conditional_edges(
        "retrieve",
        route_after_retrieval,
        {"evidence": "build_context", "empty": "no_evidence"},
    )
    graph.add_edge("build_context", "generate")
    graph.add_edge("generate", "map_citations")
    graph.add_edge("map_citations", END)
    graph.add_edge("no_evidence", END)
    # No checkpointer/store: questions do not share state or persist evidence.
    return graph.compile(name="enterprise_rag")
