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
                "你是一个企业知识助手。"
                "你只能根据提供的企业资料回答问题。"
                "如果资料中没有答案，请明确回答："
                "根据当前企业资料无法确定。"
                "不要编造信息。"
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

def ask_llm(question: str) -> str:
    try:
        response = client.responses.create(
            model="deepseek-flash",
            instructions=(
                "你是一个企业知识助手。"
                "回答必须简洁、准确。"
                "如果不确定，就明确说不知道，不要编造。"
            ),
            input=question
        )

        return response.output_text

    except Exception as e:
        return f"LLM API 调用失败：{e}"
    