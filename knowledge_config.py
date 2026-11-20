"""The one official business corpus used by indexing and retrieval."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load local configuration before reading any RAG_* or DEEPSEEK_* setting.
load_dotenv()

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "cnooc"
# Override to build side-by-side indexes, e.g. RAG_DB_PATH=chroma_db_page RAG_CHUNKER=page.
DB_PATH = Path(os.getenv("RAG_DB_PATH", "")).expanduser() if os.getenv("RAG_DB_PATH") else ROOT / "chroma_db"
if not DB_PATH.is_absolute():
    DB_PATH = ROOT / DB_PATH
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
# The reranker sees this many fused candidates. The evaluation script reads the
# same value, so reported metrics describe the configuration that is served.
DEFAULT_CANDIDATE_K = _env_int("RAG_CANDIDATE_K", 20)
MAX_TOP_K = _env_int("RAG_MAX_TOP_K", 10)
MAX_QUESTION_LENGTH = _env_int("RAG_MAX_QUESTION_LENGTH", 2000)
LLM_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
LLM_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
LLM_TIMEOUT_SECONDS = _env_float("DEEPSEEK_TIMEOUT_SECONDS", 30.0)
LLM_MAX_RETRIES = _env_int("DEEPSEEK_MAX_RETRIES", 1)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
# Evidence gate: refuse without calling the LLM when the best reranked chunk
# scores below this value (bge-reranker-base, sigmoid 0..1). Calibrate with
# ``python eval/run_cnooc_eval.py``; its report prints a threshold sweep.
# 2026-11-21 calibration (structured index, 309 chunks): answerable top-1 scores
# ≥ 0.878; abstention top-1 scores 0.026 / 0.033 / 0.087 / 0.331 / 0.763.
MIN_RERANK_SCORE = _env_float("RAG_MIN_RERANK_SCORE", 0.3)
# "structured" follows clause numbering and may cross pages; "page" is the
# original P0 splitter. Changing it requires ``python index_documents.py``.
CHUNKER = os.getenv("RAG_CHUNKER", "structured").strip().lower()
# Bumped whenever chunk text or the embedded representation changes, so the
# indexer knows an existing collection must be rebuilt.
# The Traditional→Simplified backend (OpenCC or the built-in table) changes the
# embedded text too, so it is part of the format. Checked without importing
# rag_core so this module stays dependency-free (see test_app.ConfigLoadingTests);
# must match rag_core.textnorm.t2s_backend().
import importlib.util as _importlib_util  # noqa: E402

T2S_BACKEND = "opencc" if _importlib_util.find_spec("opencc") is not None else "builtin-table"
INDEX_FORMAT = f"v2-{CHUNKER}-normalized-{T2S_BACKEND}"
# Optional answer persona. Empty (default) keeps the neutral enterprise tone.
PERSONA = os.getenv("RAG_PERSONA", "").strip()
MAX_HISTORY_TURNS = _env_int("RAG_MAX_HISTORY_TURNS", 6)
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
