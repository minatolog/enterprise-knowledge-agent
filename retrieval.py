"""Vector retrieval from the official CNOOC collection."""

import chromadb
from sentence_transformers import SentenceTransformer

from knowledge_config import COLLECTION_NAME, DB_PATH, EMBEDDING_MODEL
from rag_core.textnorm import normalize

_model = None
_collection = None

METADATA_FIELDS = (
    "source", "relative_path", "knowledge_base", "page_start", "page_end",
    "section", "source_url", "title", "chunker",
)


def get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(DB_PATH))
        _collection = client.get_collection(name=COLLECTION_NAME)
    return _collection


def reset_cache() -> None:
    """Forget the cached collection handle (used after re-indexing and in evaluation)."""
    global _collection
    _collection = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed_query(question: str) -> list[float]:
    # Documents are embedded in normalised form (Simplified Chinese, repaired
    # spacing), so the query must use the same representation.
    return get_model().encode(normalize(question), normalize_embeddings=True).tolist()


def record_from(chunk_id: str, document: str, metadata: dict, **scores) -> dict:
    record = {"chunk_id": chunk_id, "text": document}
    for key in METADATA_FIELDS:
        record[key] = metadata.get(key, "" if key not in {"page_start", "page_end"} else 0)
    record["source_url"] = metadata.get("source_url")
    record.update(scores)
    return record


def retrieve_top_k(question: str, k: int = 3) -> list[dict]:
    collection = get_collection()
    count = collection.count()
    if not count:
        return []
    result = collection.query(
        query_embeddings=[embed_query(question)],
        n_results=min(k, count),
        include=["documents", "metadatas", "distances"],
    )
    return [
        record_from(chunk_id, document, metadata, distance=distance)
        for chunk_id, document, metadata, distance in zip(
            result["ids"][0], result["documents"][0],
            result["metadatas"][0], result["distances"][0]
        )
    ]
