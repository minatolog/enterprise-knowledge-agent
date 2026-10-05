from pydantic import BaseModel


class RAGResponse(BaseModel):
    answer: str
    sources: list[str]
    retrieval_score: float