"""LangChain interfaces over the existing retrieval and DeepSeek implementations."""

from typing import Any, Callable

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import RunnableLambda
from pydantic import Field


class HybridRAGRetriever(BaseRetriever):
    """Keep the existing BM25 + Dense + RRF + reranker algorithm and metadata."""

    backend: Callable[..., list[dict[str, Any]]] = Field(exclude=True, repr=False)
    k: int = Field(default=3, ge=1)
    candidate_k: int = Field(default=5, ge=1)

    def _get_relevant_documents(self, query: str) -> list[Document]:
        records = self.backend(
            question=query, k=self.k, candidate_k=max(self.k, self.candidate_k)
        ) or []
        return [
            Document(
                page_content=record.get("text", ""),
                metadata={key: value for key, value in record.items() if key != "text"},
            )
            for record in records
        ]


def document_to_record(document: Document) -> dict[str, Any]:
    return {**document.metadata, "text": document.page_content}


def generation_runnable(backend: Callable[..., str]) -> RunnableLambda:
    """Expose the current provider as a Runnable without changing its wire protocol."""
    return RunnableLambda(
        lambda inputs: backend(question=inputs["question"], context=inputs["context"]),
        name="enterprise_evidence_generation",
    )
