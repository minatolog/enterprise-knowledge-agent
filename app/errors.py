"""Application errors with stable API codes and safe messages."""


class ApplicationError(RuntimeError):
    """Base class for errors that can be returned safely to API callers."""

    code = "APPLICATION_ERROR"
    status_code = 500
    default_message = "应用错误"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class QuestionValidationError(ApplicationError):
    code = "INVALID_REQUEST"
    status_code = 422
    default_message = "问题不合法"


class IndexNotReadyError(ApplicationError):
    code = "INDEX_NOT_READY"
    status_code = 503
    default_message = "知识库索引未就绪，请先运行 index_documents.py"


class RetrievalError(ApplicationError):
    code = "RETRIEVAL_FAILED"
    status_code = 503
    default_message = "检索失败：索引或模型未就绪"


class LLMConfigurationError(ApplicationError):
    code = "LLM_NOT_CONFIGURED"
    status_code = 503
    default_message = "LLM 未配置，请设置 DEEPSEEK_API_KEY"


class LLMRequestError(ApplicationError):
    code = "LLM_REQUEST_FAILED"
    status_code = 502
    default_message = "LLM 请求失败，请稍后重试"
