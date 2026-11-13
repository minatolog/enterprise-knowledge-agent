"""Immutable per-tenant indexes; SQL pointer publication is the commit point."""
import hashlib
import time
import uuid
from pathlib import Path

from filelock import FileLock
from sqlalchemy import select

from app.enterprise.db import active, documents, releases
from app.enterprise.parsing import parse_bytes


class Index:
    def __init__(self, settings, db, objects, embedder=None, reranker=None):
        import chromadb
        self.settings, self.db, self.objects = settings, db, objects
        self.client = chromadb.PersistentClient(path=str(settings.root / "chroma"))
        self._embedder, self._reranker = embedder, reranker
        (settings.root / "locks").mkdir(exist_ok=True)

    def lock(self, tenant):
        return FileLock(str(self.settings.root / "locks" / (hashlib.sha256(tenant.encode()).hexdigest() + ".lock")), timeout=120)

    def embed(self, texts):
        if self._embedder is None:
            from retrieval import get_model
            self._embedder = get_model()
        output = self._embedder.encode(texts, normalize_embeddings=True)
        return output.tolist() if hasattr(output, "tolist") else output

    def build(self, tenant):
        with self.lock(tenant):
            rows = self.db.rows(select(documents).where(documents.c.tenant == tenant, documents.c.deleted == 0))
            identity = uuid.uuid4().hex
            collection = self.client.create_collection(f"release_{identity}")
            manifest = {}
            total = 0
            try:
                for document in rows:
                    manifest[document["id"]] = document
                    data = self.objects.get(document["object_key"])
                    pages = parse_bytes(data, Path(document["object_key"]).suffix, self.settings.parser)
                    records = []
                    for page in pages:
                        text = page["text"].strip()
                        # Bound each chunk using Unicode codepoints without splitting UTF-8 bytes.
                        for start in range(0, len(text), 1000):
                            body = text[start:start + 1200]
                            if body:
                                records.append((f'{document["id"]}:{document["version"]}:{page["page_number"]}:{start}', body, {
                                    "document_id": document["id"], "version": document["version"],
                                    "source": document["title"], "relative_path": f'documents/{document["id"]}',
                                    "page_start": page["page_number"], "page_end": page["page_number"],
                                    "section": "", "knowledge_base": tenant,
                                }))
                    if not records:
                        raise ValueError("document has no content")
                    for start in range(0, len(records), 32):
                        batch = records[start:start + 32]
                        collection.add(ids=[r[0] for r in batch], documents=[r[1] for r in batch],
                            metadatas=[r[2] for r in batch], embeddings=self.embed([r[1] for r in batch]))
                    total += len(records)
                if collection.count() != total:
                    raise RuntimeError("index consistency check failed")
                with self.db.engine.begin() as connection:
                    connection.execute(releases.insert().values(id=identity, tenant=tenant, manifest=manifest, created=time.time()))
                    connection.execute(active.delete().where(active.c.tenant == tenant))
                    connection.execute(active.insert().values(tenant=tenant, release_id=identity))
                return identity
            except Exception:
                self.client.delete_collection(collection.name)
                raise

    def rollback(self, tenant, release_id):
        with self.lock(tenant), self.db.engine.begin() as connection:
            release = connection.execute(select(releases).where(releases.c.tenant == tenant, releases.c.id == release_id)).first()
            if not release:
                raise ValueError("release not found")
            self.client.get_collection(f"release_{release_id}")
            connection.execute(active.delete().where(active.c.tenant == tenant))
            connection.execute(active.insert().values(tenant=tenant, release_id=release_id))

    def allowed(self, principal, release):
        if not release:
            return []
        live = self.db.rows(select(documents).where(documents.c.tenant == principal.tenant, documents.c.deleted == 0))
        return [row["id"] for row in live if row["id"] in release["manifest"] and
                ("admin" in principal.roles or set(row["groups"]) & set(principal.groups))]

    def retrieve(self, question, *, release, allowed, k=3, candidate_k=10):
        if not allowed or not release:
            return []
        import jieba
        from rank_bm25 import BM25Okapi
        collection = self.client.get_collection(f'release_{release["id"]}')
        where = {"document_id": {"$in": allowed}}
        # Both branches read only authorized records, before scoring and reranking.
        authorized = collection.get(where=where, include=["documents", "metadatas"])
        if not authorized["ids"]:
            return []
        records = {identity: {**meta, "chunk_id": identity, "text": body,
            "source_url": f'/api/v2/documents/{meta["document_id"]}/original?release_id={release["id"]}'}
            for identity, body, meta in zip(authorized["ids"], authorized["documents"], authorized["metadatas"])}
        budget = min(max(candidate_k, k), len(records))
        dense = collection.query(query_embeddings=self.embed([question]), where=where, n_results=budget)["ids"][0]
        ids = authorized["ids"]
        scores = BM25Okapi([list(jieba.cut(records[i]["text"])) for i in ids]).get_scores(list(jieba.cut(question)))
        sparse = sorted(ids, key=lambda identity: scores[ids.index(identity)], reverse=True)[:budget]
        fused = {}
        for results in (dense, sparse):
            for rank, identity in enumerate(results, 1):
                fused[identity] = fused.get(identity, 0) + 1 / (60 + rank)
        candidates = [records[i] for i in sorted(fused, key=fused.get, reverse=True)[:budget]]
        if self._reranker is None:
            from sentence_transformers import CrossEncoder
            from knowledge_config import RERANKER_MODEL
            self._reranker = CrossEncoder(RERANKER_MODEL)
        scores = self._reranker.predict([(question, record["text"]) for record in candidates])
        for record, score in zip(candidates, scores):
            record["rerank_score"] = float(score)
        return sorted(candidates, key=lambda record: record["rerank_score"], reverse=True)[:k]
