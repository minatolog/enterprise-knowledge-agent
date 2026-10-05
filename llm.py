import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

def answer_with_context(question: str, context: str) -> str:
    try:
        response = client.responses.create(
            model="deepseek-flash",

            instructions=(
                "你是企业知识助手。"
                "只能依据提供的企业资料回答。"
                "不要使用资料之外的信息。"
                "如果资料无法回答问题，就回答："
                "根据当前企业资料无法确定。"
            ),

            input=f"""
企业资料：

{context}

用户问题：

{question}
"""
        )

        return response.output_text

    except Exception as e:
        return f"LLM API 调用失败：{e}"
        