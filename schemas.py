
from pydantic import BaseModel, Field, field_validator

from knowledge_config import DEFAULT_TOP_K, MAX_QUESTION_LENGTH, MAX_TOP_K


def normalize_question(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("问题必须是字符串")
    value = value.strip()
    if not value:
        raise ValueError("问题不能为空")
    if len(value) > MAX_QUESTION_LENGTH:
        raise ValueError(f"问题长度不能超过 {MAX_QUESTION_LENGTH} 个字符")
    return value


class RAGResponse(BaseModel):
    """Legacy CLI response; fields are kept for backward compatibility."""

    answer: str
    sources: list[str] = Field(default_factory=list)
    rerank_score: float | None = None


class SourceItem(BaseModel):
    chunk_id: str
    source: str
    relative_path: str
    page_start: int
    page_end: int
    source_url: str | None = None
    section: str = ""
    label: str
    rerank_score: float | None = None


class QueryRequest(BaseModel):
    question: str = Field(..., max_length=MAX_QUESTION_LENGTH)
    top_k: int = Field(default=DEFAULT_TOP_K, ge=1, le=MAX_TOP_K, strict=True)

    @field_validator("question")
    @classmethod
    def _validate_question(cls, value: str) -> str:
        return normalize_question(value)


class QueryResponse(BaseModel):
    request_id: str
    answer: str
    sources: list[SourceItem] = Field(default_factory=list)
    rerank_score: float | None = None
    retrieval_count: int = 0
    timings_ms: dict[str, float] = Field(default_factory=dict)


class DocumentInfo(BaseModel):
    source: str
    relative_path: str
    chunk_count: int
    page_start: int
    page_end: int
    source_url: str | None = None
    knowledge_base: str | None = None


class DocumentsResponse(BaseModel):
    request_id: str
    collection: str
    indexed_document_count: int
    indexed_chunk_count: int
    documents: list[DocumentInfo]


class HealthResponse(BaseModel):
    status: str


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str
