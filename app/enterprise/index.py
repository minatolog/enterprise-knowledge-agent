"""Immutable per-tenant indexes; SQL pointer publication is the commit point.

Each publish creates a new Chroma collection (a *release*). Documents whose
id/version/digest are unchanged since the active release are copied together
with their stored embeddings instead of being parsed and embedded again; a
document that fails to parse is reported in the release ``_meta`` and skipped
so one bad file cannot block every other update. Old release collections are
garbage-collected beyond ``settings.keep_releases``.
"""
import hashlib
import logging
import threading
import time
import uuid
from collections import OrderedDict
from pathlib import Path

from filelock import FileLock
from sqlalchemy import select

from app.enterprise.db import active, documents, releases
from app.enterprise.parsing import parse_bytes
from rag_core.chunking import chunk_pages, search_text
from rag_core.search import BM25Index, Reranker, hybrid_search
from rag_core.textnorm import normalize

logger = logging.getLogger(__name__)
META_KEY = "_meta"
RECORD_FIELDS = ("document_id", "version", "source", "title", "relative_path",
                 "page_start", "page_end", "section", "knowledge_base", "chunker")


def release_documents(manifest):
    """Document entries of a release manifest (excluding the ``_meta`` block)."""
    return {key: value for key, value in (manifest or {}).items() if key != META_KEY}


class Index:
    def __init__(self, settings, db, objects, embedder=None, reranker=None):
        import chromadb
        self.settings, self.db, self.objects = settings, db, objects
        self.client = chromadb.PersistentClient(path=str(settings.root / "chroma"))
        self._embedder = embedder
        if reranker is not None and not hasattr(reranker, "rerank"):
            reranker = Reranker("injected", model=reranker)
        self._reranker = reranker
        self._sparse = OrderedDict()
        self._sparse_lock = threading.Lock()
        (settings.root / "locks").mkdir(exist_ok=True)

    @property
    def index_format(self):
        from rag_core.textnorm import t2s_backend
        return f"v2-{self.settings.chunker}-normalized-{t2s_backend()}"

    def lock(self, tenant):
        return FileLock(str(self.settings.root / "locks" / (hashlib.sha256(tenant.encode()).hexdigest() + ".lock")), timeout=120)

    def embed(self, texts):
        if self._embedder is None:
            from retrieval import get_model
            self._embedder = get_model()
        output = self._embedder.encode(texts, normalize_embeddings=True)
        return output.tolist() if hasattr(output, "tolist") else output

    def reranker(self):
        if self._reranker is None:
            from knowledge_config import RERANKER_MODEL
            self._reranker = Reranker(RERANKER_MODEL)
        return self._reranker

    # ------------------------------------------------------------------ build
    def _chunk_document(self, document):
        data = self.objects.get(document["object_key"])
        pages = parse_bytes(data, Path(document["object_key"]).suffix, self.settings.parser)
        chunks = chunk_pages(pages, relative_path=f'documents/{document["id"]}', strategy=self.settings.chunker)
        records = []
        for number, chunk in enumerate(chunks, start=1):
            metadata = {
                "document_id": document["id"], "version": document["version"],
                "source": document["title"], "title": document["title"],
                "relative_path": f'documents/{document["id"]}',
                "page_start": chunk["page_start"], "page_end": chunk["page_end"],
                "section": chunk["section"], "knowledge_base": document["tenant"],
                "chunker": self.settings.chunker,
            }
            identity = f'{document["id"]}:{document["version"]}:p{chunk["page_start"]}:s{number}'
            records.append((identity, chunk["text"], metadata))
        if not records:
            raise ValueError("document has no content")
        embeddings = []
        for start in range(0, len(records), 32):
            batch = records[start:start + 32]
            embeddings.extend(self.embed([search_text({**meta, "text": body}) for _, body, meta in batch]))
        return records, embeddings

    def _reusable(self, previous, document, any_version=False):
        """Copy a document's records + embeddings from the active release.

        Normally only when the document is unchanged. With ``any_version`` the
        previously published version is returned even if a newer one exists;
        it is the fallback when the new version cannot be parsed.
        """
        if not previous:
            return None
        manifest = previous["manifest"] or {}
        if (manifest.get(META_KEY) or {}).get("format") != self.index_format:
            return None
        old = release_documents(manifest).get(document["id"])
        if not old:
            return None
        if not any_version and (old.get("version") != document["version"] or old.get("digest") != document["digest"]):
            return None
        try:
            collection = self.client.get_collection(f'release_{previous["id"]}')
            stored = collection.get(where={"$and": [{"document_id": document["id"]}, {"version": old["version"]}]},
                                    include=["documents", "metadatas", "embeddings"])
        except Exception:
            return None
        if not stored["ids"]:
            return None
        records = list(zip(stored["ids"], stored["documents"], stored["metadatas"]))
        embeddings = [list(map(float, vector)) for vector in stored["embeddings"]]
        return records, embeddings

    def build(self, tenant):
        with self.lock(tenant):
            rows = self.db.rows(select(documents).where(documents.c.tenant == tenant, documents.c.deleted == 0))
            previous = self.db.release(tenant)
            identity = uuid.uuid4().hex
            collection = self.client.create_collection(f"release_{identity}")
            manifest, failures = {}, []
            total = reused = embedded = 0
            try:
                for document in rows:
                    try:
                        prepared = self._reusable(previous, document)
                        if prepared is not None:
                            reused += 1
                        else:
                            prepared = self._chunk_document(document)
                            embedded += 1
                    except Exception as exc:  # isolate one bad document
                        logger.warning("index_document_failed document_id=%s error_type=%s", document["id"], type(exc).__name__)
                        # Keep serving the last published version of this document, if any.
                        fallback = self._reusable(previous, document, any_version=True)
                        kept = release_documents(previous["manifest"]).get(document["id"]) if fallback else None
                        failures.append({"document_id": document["id"], "title": document["title"],
                                         "version": document["version"], "error": type(exc).__name__,
                                         "message": str(exc)[:200],
                                         "kept_version": kept["version"] if kept else None})
                        if fallback is None:
                            continue
                        prepared, document = fallback, kept
                        reused += 1
                    records, vectors = prepared
                    for start in range(0, len(records), 64):
                        batch = records[start:start + 64]
                        collection.add(ids=[r[0] for r in batch], documents=[r[1] for r in batch],
                            metadatas=[r[2] for r in batch], embeddings=vectors[start:start + 64])
                    total += len(records)
                    manifest[document["id"]] = document
                if rows and not manifest:
                    raise ValueError(f"no document could be indexed ({len(failures)} failed)")
                if failures and not any(f["kept_version"] is None for f in failures) and len(failures) == len(rows):
                    # Nothing new could be parsed and every document fell back to
                    # its published version: keep the current release instead of
                    # publishing an identical copy.
                    raise ValueError(f"no document could be indexed ({len(failures)} failed); current release kept")
                if collection.count() != total:
                    raise RuntimeError("index consistency check failed")
                manifest[META_KEY] = {"format": self.index_format, "chunks": total, "reused": reused,
                                      "embedded": embedded, "failures": failures}
                with self.db.engine.begin() as connection:
                    connection.execute(releases.insert().values(id=identity, tenant=tenant, manifest=manifest, created=time.time()))
                    connection.execute(active.delete().where(active.c.tenant == tenant))
                    connection.execute(active.insert().values(tenant=tenant, release_id=identity))
            except Exception:
                self.client.delete_collection(collection.name)
                raise
            self._collect_garbage(tenant, identity)
            return identity

    def _collect_garbage(self, tenant, active_id):
        keep = max(1, int(getattr(self.settings, "keep_releases", 5)))
        rows = self.db.rows(select(releases.c.id).where(releases.c.tenant == tenant).order_by(releases.c.created.desc()))
        for row in rows[keep:]:
            if row["id"] == active_id:
                continue
            try:
                self.client.delete_collection(f'release_{row["id"]}')
            except Exception:
                pass
            with self.db.engine.begin() as connection:
                connection.execute(releases.delete().where(releases.c.id == row["id"]))
            with self._sparse_lock:
                self._sparse.pop(row["id"], None)

    def rollback(self, tenant, release_id):
        with self.lock(tenant), self.db.engine.begin() as connection:
            release = connection.execute(select(releases).where(releases.c.tenant == tenant, releases.c.id == release_id)).first()
            if not release:
                raise ValueError("release not found")
            try:
                self.client.get_collection(f"release_{release_id}")
            except Exception as exc:
                raise ValueError("release snapshot is no longer available") from exc
            connection.execute(active.delete().where(active.c.tenant == tenant))
            connection.execute(active.insert().values(tenant=tenant, release_id=release_id))

    # -------------------------------------------------------------- retrieval
    def allowed(self, principal, release):
        if not release:
            return []
        included = release_documents(release["manifest"])
        live = self.db.rows(select(documents).where(documents.c.tenant == principal.tenant, documents.c.deleted == 0))
        return [row["id"] for row in live if row["id"] in included and
                ("admin" in principal.roles or set(row["groups"]) & set(principal.groups))]

    def _records(self, release_id, identities, documents_, metadatas):
        return [{**{key: meta.get(key) for key in RECORD_FIELDS}, "chunk_id": identity, "text": body,
                 "source_url": f'/api/v2/documents/{meta["document_id"]}/original?release_id={release_id}'}
                for identity, body, meta in zip(identities, documents_, metadatas)]

    def sparse_index(self, release_id):
        """One BM25 index per release, built once; ACL filtering is applied per query."""
        with self._sparse_lock:
            if release_id in self._sparse:
                self._sparse.move_to_end(release_id)
                return self._sparse[release_id]
        collection = self.client.get_collection(f"release_{release_id}")
        stored = collection.get(include=["documents", "metadatas"])
        index = BM25Index(self._records(release_id, stored["ids"], stored["documents"], stored["metadatas"])) if stored["ids"] else None
        with self._sparse_lock:
            self._sparse[release_id] = index
            while len(self._sparse) > 8:
                self._sparse.popitem(last=False)
        return index

    def retrieve(self, question, *, release, allowed, k=3, candidate_k=10):
        if not allowed or not release:
            return []
        release_id = release["id"]
        collection = self.client.get_collection(f"release_{release_id}")
        allowed_set = set(allowed)
        where = {"document_id": {"$in": sorted(allowed_set)}}
        sparse = self.sparse_index(release_id)
        if sparse is None:
            return []

        def dense(query, budget):
            # Both branches read only authorized records, before scoring and reranking.
            result = collection.query(query_embeddings=self.embed([normalize(query)]), where=where,
                                      n_results=budget, include=["documents", "metadatas", "distances"])
            records = self._records(release_id, result["ids"][0], result["documents"][0], result["metadatas"][0])
            for record, distance in zip(records, result["distances"][0]):
                record["distance"] = distance
            return records

        def lexical(query, budget):
            return sparse.search(query, budget, allowed=lambda record: record["document_id"] in allowed_set)

        return hybrid_search(question, dense=dense, sparse=lexical, reranker=self.reranker(),
                             k=k, candidate_k=max(candidate_k, k))
