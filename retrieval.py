"""Vector retrieval from the official CNOOC collection."""

import chromadb
from sentence_transformers import SentenceTransformer

from knowledge_config import COLLECTION_NAME, DB_PATH, EMBEDDING_MODEL

_model = None
_collection = None


def get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(DB_PATH))
        _collection = client.get_collection(name=COLLECTION_NAME)
    return _collection


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def retrieve_top_k(question: str, k: int = 3) -> list[dict]:
    collection = get_collection()
    if not collection.count():
        return []
    question_embedding = get_model().encode(question, normalize_embeddings=True).tolist()
    result = collection.query(
        query_embeddings=[question_embedding],
        n_results=min(k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    return [
        {
            "chunk_id": chunk_id,
            "text": document,
            "source": metadata["source"],
            "relative_path": metadata["relative_path"],
            "knowledge_base": metadata["knowledge_base"],
            "page_start": metadata["page_start"],
            "page_end": metadata["page_end"],
            "section": metadata["section"],
            "source_url": metadata["source_url"],
            "distance": distance,
        }
        for chunk_id, document, metadata, distance in zip(
            result["ids"][0], result["documents"][0],
            result["metadatas"][0], result["distances"][0]
        )
    ]
