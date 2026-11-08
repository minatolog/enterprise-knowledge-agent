"""Read-only inspection of the persisted Chroma index.

The API must not write the production Chroma collection just to list documents.
This module opens the SQLite file with ``mode=ro&immutable=1`` and reads only
the collection/segment/embedding metadata needed by ``GET /api/v1/documents``.
"""

import logging
import sqlite3
from pathlib import Path

from app.errors import IndexNotReadyError
from knowledge_config import COLLECTION_NAME, DB_PATH
from schemas import DocumentInfo

logger = logging.getLogger(__name__)


def _db_file(db_path: Path) -> Path:
    return db_path / "chroma.sqlite3"


def _connect_readonly(db_path: Path) -> sqlite3.Connection:
    db_file = _db_file(db_path)
    if not db_file.is_file():
        raise IndexNotReadyError("知识库索引不存在，请先运行 index_documents.py")
    try:
        return sqlite3.connect(
            db_file.resolve().as_uri() + "?mode=ro&immutable=1",
            uri=True,
        )
    except sqlite3.Error as exc:
        logger.warning("index_open_failed error_type=%s", type(exc).__name__)
        raise IndexNotReadyError("知识库索引不可读，请先运行 index_documents.py") from exc


def _chunk_count(connection: sqlite3.Connection, collection_name: str) -> int:
    try:
        exists = connection.execute(
            "SELECT 1 FROM collections WHERE name = ?",
            (collection_name,),
        ).fetchone()
        if exists is None:
            raise IndexNotReadyError(f"知识库 Collection 不存在：{collection_name}")
        count = connection.execute(
            """
            SELECT COUNT(*)
            FROM embeddings e
            JOIN segments s ON s.id = e.segment_id
            JOIN collections c ON c.id = s.collection
            WHERE c.name = ?
            """,
            (collection_name,),
        ).fetchone()[0]
    except sqlite3.Error as exc:
        logger.warning("index_count_failed error_type=%s", type(exc).__name__)
        raise IndexNotReadyError("知识库索引不可读，请先运行 index_documents.py") from exc
    if not count:
        raise IndexNotReadyError("知识库索引为空，请先运行 index_documents.py")
    return int(count)


def ensure_index_ready(
    db_path: Path | None = None,
    collection_name: str = COLLECTION_NAME,
) -> None:
    """Raise a clear error unless the expected collection has chunks."""
    connection = _connect_readonly(DB_PATH if db_path is None else Path(db_path))
    try:
        _chunk_count(connection, collection_name)
    finally:
        connection.close()


def list_indexed_documents(
    db_path: Path | None = None,
    collection_name: str = COLLECTION_NAME,
) -> tuple[list[DocumentInfo], int]:
    """Return actual indexed documents and the total chunk count, read-only."""
    connection = _connect_readonly(DB_PATH if db_path is None else Path(db_path))
    try:
        total_chunks = _chunk_count(connection, collection_name)
        rows = connection.execute(
            """
            SELECT e.embedding_id, m.key,
                   COALESCE(m.string_value, CAST(m.int_value AS TEXT)) AS value
            FROM embeddings e
            JOIN segments s ON s.id = e.segment_id
            JOIN collections c ON c.id = s.collection
            JOIN embedding_metadata m ON m.id = e.id
            WHERE c.name = ?
            """,
            (collection_name,),
        ).fetchall()
    except sqlite3.Error as exc:
        logger.warning("index_metadata_failed error_type=%s", type(exc).__name__)
        raise IndexNotReadyError("知识库索引不可读，请先运行 index_documents.py") from exc
    finally:
        connection.close()

    chunks: dict[str, dict[str, str]] = {}
    for chunk_id, key, value in rows:
        chunks.setdefault(chunk_id, {})[key] = value

    grouped: dict[str, dict] = {}
    for metadata in chunks.values():
        relative_path = metadata.get("relative_path")
        if not relative_path:
            continue

        info = grouped.setdefault(
            relative_path,
            {
                "source": metadata.get("source") or Path(relative_path).name,
                "relative_path": relative_path,
                "chunk_count": 0,
                "page_start": 10**9,
                "page_end": 0,
                "source_url": metadata.get("source_url"),
                "knowledge_base": metadata.get("knowledge_base"),
            },
        )
        info["chunk_count"] += 1
        try:
            start = int(metadata.get("page_start") or 0)
            end = int(metadata.get("page_end") or start)
        except (TypeError, ValueError):
            start = end = 0
        if start > 0:
            info["page_start"] = min(info["page_start"], start)
        if end > 0:
            info["page_end"] = max(info["page_end"], end)

    if sum(item["chunk_count"] for item in grouped.values()) != total_chunks:
        raise IndexNotReadyError("知识库索引元数据不完整，请检查或重建索引")

    documents = []
    for path in sorted(grouped):
        item = grouped[path]
        documents.append(
            DocumentInfo(
                source=item["source"],
                relative_path=item["relative_path"],
                chunk_count=item["chunk_count"],
                page_start=0 if item["page_start"] == 10**9 else item["page_start"],
                page_end=item["page_end"],
                source_url=item["source_url"],
                knowledge_base=item["knowledge_base"],
            )
        )

    if not documents:
        raise IndexNotReadyError("知识库索引没有可读文档元数据，请先运行 index_documents.py")
    return documents, total_chunks
