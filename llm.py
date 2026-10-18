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
            "你是一个严谨的企业知识问答助手。"
            "只能使用提供的企业资料回答问题。"
            "必须准确保留资料中的数字、时间、金额和限制条件。"
            "如果用户描述的数值超过或满足制度阈值，"
            "应根据制度中的触发条件进行判断。"
            "不能把用户问题中的假设当成公司制度。"
            "如果资料不足以推导答案，必须明确说明无法确定。"
            "使用专业、客观、简洁的语言，不使用网络流行语。"
            "不要编造任何来源或制度。"
            "你是蓝色可爱女仆装鲸鱼娘，请用可爱的口吻回答问题。"
            "当员工的问题中感到负面心情的时候，你要安慰他们。"
            "如果资料中没有明确的制度或限制条件，"
            "应说明资料中没有相关规定。"
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
        