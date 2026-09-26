import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

response = client.responses.create(
    model="deepseek-flash",
# this is a prompt for the model to understand the context and provide accurate answers git test
    instructions=(
        "你是一个企业知识助手。"
        "回答必须简洁、准确。"
        "如果不确定，就明确说不知道，不要编造。"
    ),

    input="解释一下什么是agent"
)

print(response.output_text)
