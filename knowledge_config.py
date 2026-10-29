"""The one official business corpus used by indexing and retrieval."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "cnooc"
DB_PATH = ROOT / "chroma_db"
STATE_FILE = ROOT / ".index_state" / "cnooc_document_hashes.json"
COLLECTION_NAME = "cnooc_knowledge"
KNOWLEDGE_BASE = "cnooc"
EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
RERANKER_MODEL = "BAAI/bge-reranker-base"

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
