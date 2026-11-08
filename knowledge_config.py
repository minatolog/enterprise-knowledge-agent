"""The one official business corpus used by indexing and retrieval."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load local configuration before reading any RAG_* or DEEPSEEK_* setting.
load_dotenv()

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "cnooc"
DB_PATH = ROOT / "chroma_db"
STATE_FILE = ROOT / ".index_state" / "cnooc_document_hashes.json"
COLLECTION_NAME = "cnooc_knowledge"
KNOWLEDGE_BASE = "cnooc"
EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
RERANKER_MODEL = "BAAI/bge-reranker-base"


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"环境变量 {name} 必须是整数") from exc


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"环境变量 {name} 必须是数字") from exc


# Application defaults shared by the CLI and API.
DEFAULT_TOP_K = _env_int("RAG_TOP_K", 3)
DEFAULT_CANDIDATE_K = _env_int("RAG_CANDIDATE_K", 5)
MAX_TOP_K = _env_int("RAG_MAX_TOP_K", 10)
MAX_QUESTION_LENGTH = _env_int("RAG_MAX_QUESTION_LENGTH", 2000)
LLM_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
LLM_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
LLM_TIMEOUT_SECONDS = _env_float("DEEPSEEK_TIMEOUT_SECONDS", 30.0)
LLM_MAX_RETRIES = _env_int("DEEPSEEK_MAX_RETRIES", 1)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
API_TITLE = "Enterprise Knowledge Agent"
API_VERSION = "0.1.0"
NO_EVIDENCE_ANSWER = "根据当前企业知识库无法回答该问题。"

# Deliberate allowlist. Annual and ESG reports remain on disk but are not indexed.
INDEXED_DOCUMENTS = (
    "data/cnooc/compliance/employee_compliance.pdf",
    "data/cnooc/compliance/director_ethics_2026.pdf",
    "data/cnooc/governance/articles_2025.pdf",
    "data/cnooc/governance/nomination_committee_2025.pdf",
    "data/cnooc/governance/audit_committee.pdf",
    "data/cnooc/governance/remuneration_committee.pdf",
    "data/cnooc/governance/strategy_sustainability_committee.pdf",
)


def selected_paths(require_existing: bool = True) -> dict[str, Path]:
    paths = {name: ROOT / name for name in INDEXED_DOCUMENTS}
    for name, path in paths.items():
        if not path.resolve().is_relative_to(DATA_DIR.resolve()):
            raise ValueError(f"文件不在 CNOOC 数据目录：{name}")
        if require_existing and (not path.is_file() or path.suffix.lower() != ".pdf"):
            raise FileNotFoundError(f"正式知识库文件不存在或类型错误：{name}")
    return {name: path for name, path in paths.items() if path.is_file()}
