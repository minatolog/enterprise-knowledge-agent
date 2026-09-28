from pydantic import BaseModel


class Answer(BaseModel):
    answer: str
    confidence: float
    source: str


example = Answer(
    answer="RAG 是检索增强生成技术。",
    confidence=0.95,
    source="企业知识库"
)
schema = Answer.model_json_schema()

print(schema)
print(example)
print()
print(example.answer)
print(example.confidence)
print(example.source)