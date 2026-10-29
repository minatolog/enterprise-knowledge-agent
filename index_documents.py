"""Incrementally index only the approved CNOOC documents."""

import csv
import time

import chromadb
from sentence_transformers import SentenceTransformer

from document_tracker import calculate_file_hash, detect_changes, save_state
from ingestion import load_document
from knowledge_config import (
    COLLECTION_NAME, DATA_DIR, DB_PATH, EMBEDDING_MODEL,
    INDEXED_DOCUMENTS, KNOWLEDGE_BASE, selected_paths,
)
from rag import chunk_document


def source_rows(paths: dict) -> dict[str, dict]:
    with (DATA_DIR / "sources.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = {row["relative_path"]: row for row in csv.DictReader(handle)}
    for name, path in paths.items():
        if name not in rows or calculate_file_hash(path) != rows[name]["sha256"]:
            raise ValueError(f"来源清单或 SHA-256 与原始 PDF 不一致：{name}")
    return rows


def index_document(relative_path, path, row, model, collection) -> int:
    document = load_document(path)
    chunks = chunk_document(document)
    if not chunks:
        raise ValueError(f"文档没有有效 Chunk：{relative_path}")
    ids = [chunk["chunk_id"] for chunk in chunks]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Chunk ID 重复：{relative_path}")
    texts = [chunk["text"] for chunk in chunks]
    embeddings = model.encode(texts, normalize_embeddings=True, batch_size=32).tolist()
    metadatas = [{
        "source": chunk["source"],
        "relative_path": chunk["relative_path"],
        "knowledge_base": KNOWLEDGE_BASE,
        "page_start": chunk["page_start"],
        "page_end": chunk["page_end"],
        "section": chunk["section"],
        "source_url": row["source_url"],
    } for chunk in chunks]

    # Prepare all embeddings first. A failed encode leaves existing records intact.
    old_ids = set(collection.get(where={"relative_path": relative_path}, include=[])["ids"])
    for start in range(0, len(ids), 64):
        end = start + 64
        collection.upsert(
            ids=ids[start:end],
            documents=texts[start:end],
            embeddings=embeddings[start:end],
            metadatas=metadatas[start:end],
        )
    stale = sorted(old_ids - set(ids))
    if stale:
        collection.delete(ids=stale)
    actual = collection.get(where={"relative_path": relative_path}, include=[])["ids"]
    if set(actual) != set(ids):
        raise RuntimeError(f"写入后 Chunk ID 不一致：{relative_path}")
    return len(ids)


def verify_collection(collection, expected_paths=None) -> dict[str, int]:
    records = collection.get(include=["metadatas"])
    allowed = set(INDEXED_DOCUMENTS if expected_paths is None else expected_paths)
    if not allowed:
        raise RuntimeError("正式知识库没有任何可用 PDF")
    counts = {name: 0 for name in allowed}
    for metadata in records["metadatas"]:
        name = metadata.get("relative_path")
        if name not in allowed or metadata.get("knowledge_base") != KNOWLEDGE_BASE:
            raise RuntimeError(f"正式 Collection 混入非 CNOOC 数据：{metadata}")
        if metadata.get("page_start", 0) < 1 or metadata.get("page_end") < metadata["page_start"]:
            raise RuntimeError(f"页码 Metadata 无效：{metadata}")
        counts[name] += 1
    if not all(counts.values()):
        raise RuntimeError(f"正式 Collection 缺少文档：{counts}")
    return counts


def main():
    started = time.monotonic()
    paths = selected_paths(require_existing=False)
    rows = source_rows(paths)
    changes = detect_changes()
    client = chromadb.PersistentClient(path=str(DB_PATH))
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    existing = collection.get(include=["metadatas"])
    present = {metadata.get("relative_path") for metadata in existing["metadatas"]}
    to_index = set(changes["added"] + changes["modified"]) | (set(paths) - present)

    model = SentenceTransformer(EMBEDDING_MODEL) if to_index else None
    for name in INDEXED_DOCUMENTS:
        if name in to_index:
            count = index_document(name, paths[name], rows[name], model, collection)
            print(f"已索引：{name}，{count} chunks", flush=True)
    for name in changes["deleted"]:
        collection.delete(where={"relative_path": name})
        print(f"已清理失效文档：{name}", flush=True)

    # Also repair a stale collection when its former state file is unavailable.
    remaining = collection.get(include=["metadatas"])
    orphan_ids = [chunk_id for chunk_id, metadata in zip(
        remaining["ids"], remaining["metadatas"]
    ) if metadata.get("relative_path") not in paths]
    if orphan_ids:
        collection.delete(ids=orphan_ids)
        print(f"已清理无效 Chunk：{len(orphan_ids)}", flush=True)

    counts = verify_collection(collection, paths)
    save_state(changes["current_state"])
    print(f"Collection: {COLLECTION_NAME}; PDF: {len(counts)}; Chunks: {sum(counts.values())}")
    print("每份文档 Chunk 数：", counts)
    print(f"耗时：{time.monotonic() - started:.1f} 秒")


if __name__ == "__main__":
    main()
