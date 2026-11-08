"""DeepSeek adapter with lazy client creation and safe errors."""

import logging
import os

from openai import OpenAI

from app.errors import LLMConfigurationError, LLMRequestError
from knowledge_config import (
    LLM_BASE_URL,
    LLM_MAX_RETRIES,
    LLM_MODEL,
    LLM_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTIONS = (
    "你是一个严谨的企业知识问答助手。"
    "只能使用提供的企业资料回答问题。"
    "必须准确保留资料中的数字、时间、金额和限制条件。"
    "如果用户描述的数值超过或满足制度阈值，"
    "应根据制度中的触发条件进行判断。"
    "不能把用户问题中的假设当成公司制度。"
    "如果资料不足以推导答案，必须明确说明无法确定。"
    "使用专业、客观、简洁的语言，不使用网络流行语。"
    "不要编造任何来源或制度。"
    "每个有事实依据的结论请引用对应的资料编号，例如[资料 1]。"
    "如果提供的片段不能直接支持答案，应明确说明无法确定，不要引用无关资料。"
    "你是蓝色可爱女仆装鲸鱼娘，请用可爱的口吻回答问题。"
    "当员工的问题中感到负面心情的时候，你要安慰他们。"
    "如果资料中没有明确的制度或限制条件，"
    "应说明资料中没有相关规定。"
)


def get_client() -> OpenAI:
    """Create the client only when a real LLM call is attempted."""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise LLMConfigurationError("LLM 未配置：缺少 DEEPSEEK_API_KEY")
    return OpenAI(
        api_key=api_key,
        base_url=LLM_BASE_URL,
        timeout=LLM_TIMEOUT_SECONDS,
        max_retries=LLM_MAX_RETRIES,
    )


def answer_with_context(question: str, context: str) -> str:
    client = get_client()
    try:
        response = client.responses.create(
            model=LLM_MODEL,
            instructions=SYSTEM_INSTRUCTIONS,
            input=f"""
企业资料：

{context}

用户问题：

{question}
""",
        )
        answer = response.output_text
    except Exception as exc:
        logger.warning("llm_request_failed error_type=%s", type(exc).__name__)
        raise LLMRequestError("LLM 请求失败，请稍后重试") from exc

    if not isinstance(answer, str) or not answer.strip():
        raise LLMRequestError("LLM 未返回有效回答")
    return answer
