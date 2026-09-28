import os
import json

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel


load_dotenv()


class Answer(BaseModel):
    answer: str
    confidence: float
    source: str


client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

schema = Answer.model_json_schema()

response = client.responses.create(
    model="deepseek-flash",

    instructions=(
        "你是一个企业知识助手。"
        "请严格按照给定的 JSON Schema 返回结果。"
    ),

    input="请解释什么是 RAG，并给出置信度和信息来源。",

    text={
        "format": {
            "type": "json_schema",
            "name": "answer",
            "schema": schema
        }
    }
)

print("模型原始输出：")
print(response.output_text)

data = json.loads(response.output_text)

result = Answer.model_validate(data)

print("\nPydantic 解析结果：")
print(result)

print("\n单独读取字段：")
print("回答：", result.answer)
print("置信度：", result.confidence)
print("来源：", result.source)

from pydantic import ValidationError

print("\n--- 测试非法数据 ---")

bad_data = {
    "answer": "RAG 是检索增强生成技术。",
    "confidence": "非常高",
    "source": "企业知识库"
}

try:
    bad_result = Answer.model_validate(bad_data)
    print(bad_result)

except ValidationError as e:
    print("捕获到数据校验失败：")
    print(e)