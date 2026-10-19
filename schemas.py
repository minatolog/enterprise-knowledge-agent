
from pydantic import BaseModel, Field


class RAGResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)
    rerank_score: float | None = None
