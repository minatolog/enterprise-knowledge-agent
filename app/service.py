"""Reusable RAG question-answering service shared by the CLI and API."""

from __future__ import annotations

import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from app.errors import (
    LLMConfigurationError,
    LLMRequestError,
    QuestionValidationError,
    RetrievalError,
)
from app.index_status import ensure_index_ready
from app.langchain_adapters import HybridRAGRetriever, document_to_record, generation_runnable
from app.workflow import RAGState, build_rag_graph
from knowledge_config import (
    DEFAULT_CANDIDATE_K,
    DEFAULT_TOP_K,
    MAX_TOP_K,
    NO_EVIDENCE_ANSWER,
)
from schemas import SourceItem, normalize_question

logger = logging.getLogger(__name__)


class RetrieverProtocol(Protocol):
    def __call__(
        self,
        question: str,
        k: int,
        candidate_k: int,
    ) -> list[dict[str, Any]]: ...


class LLMProtocol(Protocol):
    def __call__(self, question: str, context: str) -> str: ...


@dataclass
class RAGResult:
    request_id: str
    answer: str
    sources: list[SourceItem]
    legacy_sources: list[str]
    rerank_score: float | None
    retrieval_count: int
    timings_ms: dict[str, float]
    retrieval_results: list[dict[str, Any]] = field(default_factory=list, repr=False)


def source_label(result: dict[str, Any]) -> str:
    """Keep the original CLI label format: relative path + PDF page."""
    start = int(result.get("page_start") or 0)
    end = int(result.get("page_end") or start)
    page = f"第{start}页" if start == end else f"第{start}–{end}页"
    return f'{result.get("relative_path", "")}，{page}'


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class RAGService:
    """One retrieval -> context -> LLM -> citation path for CLI and API."""

    def __init__(
        self,
        retriever: RetrieverProtocol | None = None,
        llm: LLMProtocol | None = None,
        index_checker: Callable[[], None] | None = None,
        default_top_k: int = DEFAULT_TOP_K,
        candidate_k: int = DEFAULT_CANDIDATE_K,
    ) -> None:
        self._retriever = retriever
        self._llm = llm
        self._index_checker = index_checker
        self.default_top_k = default_top_k
        self.candidate_k = candidate_k

        # A mock retriever is normally used for offline tests; do not require
        # the production index unless the caller asks for it explicitly.
        if self._index_checker is None:
            self._index_checker = ensure_index_ready if retriever is None else (lambda: None)
        if self.default_top_k < 1 or self.default_top_k > MAX_TOP_K:
            raise ValueError(f"default_top_k 必须在 1..{MAX_TOP_K} 之间")
        if self.candidate_k < 1:
            raise ValueError("candidate_k 必须为正整数")
        self.graph = build_rag_graph(self)

    def _get_retriever(self) -> RetrieverProtocol:
        if self._retriever is None:
            from hybrid_retrieval import retrieve_with_reranker

            self._retriever = retrieve_with_reranker
        return self._retriever

    def _get_llm(self) -> LLMProtocol:
        if self._llm is None:
            from llm import answer_with_context

            self._llm = answer_with_context
        return self._llm

    def answer(
        self,
        question: str,
        top_k: int | None = None,
        request_id: str | None = None,
        on_retrieval: Callable[[list[dict[str, Any]]], None] | None = None,
    ) -> RAGResult:
        request_id = request_id or uuid.uuid4().hex
        try:
            question = normalize_question(question)
        except ValueError as exc:
            raise QuestionValidationError(str(exc)) from exc

        if top_k is None:
            top_k = self.default_top_k
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1 or top_k > MAX_TOP_K:
            raise QuestionValidationError(f"top_k 必须在 1..{MAX_TOP_K} 之间")
        candidate_k = max(self.candidate_k, top_k)

        timings: dict[str, float] = {}
        total_start = time.perf_counter()
        logger.info(
            "query_start request_id=%s top_k=%s candidate_k=%s question_chars=%s",
            request_id,
            top_k,
            candidate_k,
            len(question),
        )

        state = self.graph.invoke({
            "question": question,
            "top_k": top_k,
            "candidate_k": candidate_k,
            "request_id": request_id,
            "on_retrieval": on_retrieval,
            "total_start": total_start,
            "timings": timings,
        })
        return state["result"]

    def _check_index(self, state: RAGState) -> dict:
        timings = dict(state["timings"])
        check_start = time.perf_counter()
        self._index_checker()
        timings["index_check_ms"] = round((time.perf_counter() - check_start) * 1000, 1)

        return {"timings": timings}

    def _retrieve(self, state: RAGState) -> dict:
        question, request_id = state["question"], state["request_id"]
        timings = dict(state["timings"])
        retrieval_start = time.perf_counter()
        try:
            retriever = HybridRAGRetriever(
                backend=self._get_retriever(), k=state["top_k"],
                candidate_k=state["candidate_k"],
            )
            documents = retriever.invoke(
                question, config={"metadata": {"request_id": request_id}}
            )
            results = [document_to_record(document) for document in documents]
        except ModuleNotFoundError as exc:
            logger.warning(
                "retrieval_dependency_missing request_id=%s error_type=%s",
                request_id,
                type(exc).__name__,
            )
            raise RetrievalError("检索依赖未安装或模型不可用") from exc
        except Exception as exc:
            logger.warning(
                "retrieval_failed request_id=%s error_type=%s",
                request_id,
                type(exc).__name__,
            )
            raise RetrievalError("检索失败：索引或模型未就绪") from exc
        timings["retrieval_ms"] = round((time.perf_counter() - retrieval_start) * 1000, 1)
        logger.info(
            "retrieval_done request_id=%s candidates=%s duration_ms=%s",
            request_id,
            len(results),
            timings["retrieval_ms"],
        )

        return {"results": results, "timings": timings}

    def _no_evidence(self, state: RAGState) -> dict:
        request_id, total_start = state["request_id"], state["total_start"]
        timings = dict(state["timings"])
        timings["llm_ms"] = 0.0
        timings["total_ms"] = round((time.perf_counter() - total_start) * 1000, 1)
        logger.info(
            "query_done request_id=%s answer=refusal sources=0 total_ms=%s",
            request_id,
            timings["total_ms"],
        )
        result = RAGResult(
            request_id=request_id,
            answer=NO_EVIDENCE_ANSWER,
            sources=[],
            legacy_sources=[],
            rerank_score=None,
            retrieval_count=0,
            timings_ms=timings,
            retrieval_results=[],
        )

        return {"result": result, "timings": timings}

    def _build_context(self, state: RAGState) -> dict:
        results, on_retrieval = state["results"], state["on_retrieval"]
        if on_retrieval is not None:
            on_retrieval(results)

        contexts: list[str] = []
        source_by_number: dict[int, SourceItem] = {}
        legacy_source_by_number: dict[int, str] = {}
        for index, result in enumerate(results, start=1):
            label = source_label(result)
            source_item = SourceItem(
                chunk_id=str(result.get("chunk_id", "")),
                source=str(result.get("source", "")),
                relative_path=str(result.get("relative_path", "")),
                page_start=int(result.get("page_start") or 0),
                page_end=int(result.get("page_end") or result.get("page_start") or 0),
                source_url=result.get("source_url"),
                section=str(result.get("section") or ""),
                label=label,
                rerank_score=_to_float(result.get("rerank_score")),
            )
            source_by_number[index] = source_item
            legacy_source_by_number[index] = label
            contexts.append(
                f"[资料 {index}]\n"
                f"来源：{label}\n"
                f"内容：{result.get('text', '')}"
            )

        context = "\n\n".join(contexts)
        return {
            "context": context,
            "source_by_number": source_by_number,
            "legacy_source_by_number": legacy_source_by_number,
        }

    def _generate(self, state: RAGState) -> dict:
        question, context = state["question"], state["context"]
        request_id = state["request_id"]
        timings = dict(state["timings"])
        llm_start = time.perf_counter()
        try:
            answer = generation_runnable(self._get_llm()).invoke(
                {"question": question, "context": context},
                config={"metadata": {"request_id": request_id}},
            )
        except LLMConfigurationError:
            raise
        except LLMRequestError as exc:
            raise LLMRequestError("LLM 请求失败，请稍后重试") from exc
        except ModuleNotFoundError as exc:
            logger.warning(
                "llm_dependency_missing request_id=%s error_type=%s",
                request_id,
                type(exc).__name__,
            )
            raise LLMConfigurationError("LLM 依赖未安装，请检查 requirements.txt") from exc
        except Exception as exc:
            logger.warning(
                "llm_failed request_id=%s error_type=%s",
                request_id,
                type(exc).__name__,
            )
            raise LLMRequestError("LLM 请求失败，请稍后重试") from exc
        timings["llm_ms"] = round((time.perf_counter() - llm_start) * 1000, 1)

        if not isinstance(answer, str) or not answer.strip():
            raise LLMRequestError("LLM 未返回有效回答")
        if answer.startswith("LLM API 调用失败："):
            raise LLMRequestError("LLM 请求失败，请稍后重试")

        return {"answer": answer, "timings": timings}

    def _map_citations(self, state: RAGState) -> dict:
        answer, results = state["answer"], state["results"]
        source_by_number = state["source_by_number"]
        legacy_source_by_number = state["legacy_source_by_number"]
        request_id, total_start = state["request_id"], state["total_start"]
        timings = dict(state["timings"])
        cited_numbers = [int(n) for n in re.findall(r"\[资料\s*(\d+)\]", answer)]
        sources: list[SourceItem] = []
        legacy_sources: list[str] = []
        seen_chunk_ids: set[str] = set()
        seen_labels: set[str] = set()
        for number in cited_numbers:
            item = source_by_number.get(number)
            if item is not None and item.chunk_id not in seen_chunk_ids:
                sources.append(item)
                seen_chunk_ids.add(item.chunk_id)
            label = legacy_source_by_number.get(number)
            if label is not None and label not in seen_labels:
                legacy_sources.append(label)
                seen_labels.add(label)

        timings["total_ms"] = round((time.perf_counter() - total_start) * 1000, 1)
        logger.info(
            "query_done request_id=%s answer_chars=%s sources=%s total_ms=%s",
            request_id,
            len(answer),
            len(sources),
            timings["total_ms"],
        )
        result = RAGResult(
            request_id=request_id,
            answer=answer,
            sources=sources,
            legacy_sources=legacy_sources,
            rerank_score=_to_float(results[0].get("rerank_score")),
            retrieval_count=len(results),
            timings_ms=timings,
            retrieval_results=results,
        )
        return {"result": result, "timings": timings}
