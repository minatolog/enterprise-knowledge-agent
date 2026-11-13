import hashlib
import json
import threading
import time
import uuid
from contextlib import contextmanager

import tiktoken
from fastapi import HTTPException
from opentelemetry.sdk.trace import TracerProvider
from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest
from sqlalchemy import select

from app.enterprise.db import documents, jobs, turns, versions
from app.service import RAGService, source_label


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def select_evidence(records, token_budget):
    encoding = tiktoken.get_encoding("cl100k_base")
    selected, seen, used = [], set(), 0
    for record in records:
        digest = fingerprint(" ".join(record["text"].split()))
        if digest in seen:
            continue
        seen.add(digest)
        text = f'[资料 {len(selected) + 1}]\n来源：{source_label(record)}\n内容：{record["text"]}'
        cost = len(encoding.encode(text + "\n\n"))
        if used + cost > token_budget:
            continue
        used += cost
        selected.append(record)
    return selected


class Runtime:
    def __init__(self, settings, db, objects, index, model=None, judge=None):
        self.settings, self.db, self.objects, self.index = settings, db, objects, index
        self.model, self.judge = model, judge
        if judge is None and settings.verify_answers:
            from app.enterprise.verification import EvidenceJudge
            self.judge = EvidenceJudge()
        self.cache, self.cache_lock = {}, threading.Lock()
        self.redis = None
        if settings.redis_url:
            import redis
            self.redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        self.registry = CollectorRegistry()
        self.requests = Counter("rag_query_total", "Query count", ["outcome"], registry=self.registry)
        self.tokens = Counter("rag_model_tokens_total", "Observed provider token usage", ["direction"], registry=self.registry)
        if self.judge and hasattr(self.judge, "on_usage"):
            self.judge.on_usage = self.record_usage
        self.latency = Histogram("rag_query_seconds", "End-to-end query duration", registry=self.registry)
        self.provider = TracerProvider()
        if settings.otlp_endpoint:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            self.provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otlp_endpoint)))
        self.tracer = self.provider.get_tracer("enterprise-rag")

    def metrics(self):
        return generate_latest(self.registry)

    def record_usage(self, usage):
        for direction in ("input", "output"):
            count = getattr(usage, direction + "_tokens", None)
            if isinstance(count, int) and count >= 0:
                self.tokens.labels(direction).inc(count)

    @contextmanager
    def span(self, name):
        # Do not place questions, evidence, identities or keys in trace attributes.
        with self.tracer.start_as_current_span(name):
            yield

    def upload(self, principal, title, data, suffix, groups, document_id=None, create_id=None):
        principal.editor()
        if not groups or any(not isinstance(group, str) or not group or len(group) > 128 for group in groups):
            raise HTTPException(422, "at least one valid ACL group is required")
        if len(data) > self.settings.max_upload_bytes or not data:
            raise HTTPException(413, "empty file or upload limit exceeded")
        if suffix not in {".pdf", ".md", ".txt", ".docx"}:
            raise HTTPException(415, "unsupported file")
        if suffix == ".docx":
            import io, zipfile
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    if len(archive.infolist()) > 10000 or sum(item.file_size for item in archive.infolist()) > 100 * 1024 * 1024:
                        raise ValueError("expanded document too large")
            except (zipfile.BadZipFile, ValueError):
                raise HTTPException(422, "invalid or oversized DOCX archive")
        identity = document_id or create_id or uuid.uuid4().hex
        with self.index.lock(principal.tenant):
            old = self.db.document(principal.tenant, identity)
            if document_id and not old:
                raise HTTPException(404, "document not found")
            if old and "admin" not in principal.roles and not set(old["groups"]) & set(principal.groups):
                raise HTTPException(404, "document not found")
            key, digest = self.objects.put(principal.tenant, data, suffix)
            version = (old["version"] + 1) if old else 1
            if old and old["digest"] == digest and set(old["groups"]) == set(groups) and old["title"] == title:
                return old
            row = dict(id=identity, tenant=principal.tenant, title=title, version=version,
                groups=sorted(set(groups)), object_key=key, digest=digest, deleted=0)
            with self.db.engine.begin() as connection:
                if old:
                    connection.execute(documents.update().where(documents.c.id == identity).values(**row))
                else:
                    connection.execute(documents.insert().values(**row))
                connection.execute(versions.insert().values(id=uuid.uuid4().hex, document_id=identity,
                    tenant=principal.tenant, version=version, object_key=key, digest=digest))
            return row

    def sync_pages(self, principal, url, rows, groups):
        result = []
        for row in rows:
            identity = hashlib.sha256((principal.tenant + url + row["external_id"]).encode()).hexdigest()[:32]
            existing = self.db.document(principal.tenant, identity)
            self.upload(principal, row["title"], row["text"].encode(), ".md", groups,
                identity if existing else None, create_id=identity)
            result.append(identity)
        return result

    def run_job(self, identity):
        from filelock import FileLock
        with FileLock(str(self.settings.root / "locks" / ("job-" + fingerprint(identity) + ".lock")), timeout=1800):
            return self._run_job(identity)

    def _run_job(self, identity):
        rows = self.db.rows(select(jobs).where(jobs.c.id == identity))
        if not rows:
            raise ValueError("job not found")
        job = rows[0]
        if job["status"] == "succeeded":
            return job["release_id"]
        with self.db.engine.begin() as connection:
            connection.execute(jobs.update().where(jobs.c.id == identity).values(status="running", attempts=jobs.c.attempts + 1, error=None))
        try:
            with self.span("ingestion.publish"):
                release = self.index.build(job["tenant"])
            with self.db.engine.begin() as connection:
                connection.execute(jobs.update().where(jobs.c.id == identity).values(status="succeeded", release_id=release))
            return release
        except Exception as exc:
            with self.db.engine.begin() as connection:
                connection.execute(jobs.update().where(jobs.c.id == identity).values(status="failed", error=type(exc).__name__))
            raise

    def acl_key(self, principal, allowed):
        return fingerprint([principal.tenant, principal.subject, sorted(principal.groups), sorted(principal.roles), sorted(allowed)])

    def history(self, principal, session_id, release, acl_key):
        rows = self.db.rows(select(turns).where(turns.c.tenant == principal.tenant,
            turns.c.subject == principal.subject, turns.c.session_id == session_id,
            turns.c.release_id == release, turns.c.acl_key == acl_key).order_by(turns.c.created.desc()).limit(10))
        return [row["payload"] for row in reversed(rows)]

    def query(self, principal, question, top_k=3, session_id=None):
        started = time.perf_counter()
        try:
            with self.span("rag.query"):
                output = self._query(principal, question, top_k, session_id)
            self.requests.labels("ok").inc()
            return output
        except Exception:
            self.requests.labels("error").inc()
            raise
        finally:
            self.latency.observe(time.perf_counter() - started)

    def _query(self, principal, question, top_k, session_id):
        release = self.db.release(principal.tenant)
        allowed = self.index.allowed(principal, release)
        release_id = release["id"] if release else "none"
        acl_key = self.acl_key(principal, allowed)
        history = self.history(principal, session_id, release_id, acl_key) if session_id else []
        cache_key = "rag:" + fingerprint([acl_key, release_id, question, top_k, history, self.settings.context_tokens])
        cached = self.redis.get(cache_key) if self.redis else None
        if not self.redis:
            with self.cache_lock:
                entry = self.cache.get(cache_key)
                cached = entry[1] if entry and entry[0] > time.time() else None
        if cached:
            output = json.loads(cached)
            output["request_id"] = uuid.uuid4().hex
            output["cached"] = True
            # Cache hits still represent a new conversation turn.
            self.save_turn(principal, session_id, release_id, acl_key, question, output)
            return output

        evidence = []
        def retrieve(question, k, candidate_k):
            with self.span("retrieval.authorized_hybrid"):
                records = self.index.retrieve(question, release=release, allowed=allowed, k=k, candidate_k=candidate_k)
                records = select_evidence(records, self.settings.context_tokens)
                evidence.extend(records)
                return records

        def generate(question, context):
            from app.enterprise.generation import generate_from_evidence
            history_text = json.dumps(history[-3:], ensure_ascii=False)[:1500] if history else "[]"
            with self.span("generation"):
                combined = question + "\n历史对话（仅辅助理解，不是制度证据）：" + history_text
                answer = self.model(question=combined, context=context) if self.model else generate_from_evidence(combined, context, self.record_usage)
            return answer

        result = RAGService(retriever=retrieve, llm=generate).answer(question, top_k=top_k)
        # Citation existence is deterministic; entailment needs a separate judge.
        import re
        cited = [int(n) for n in re.findall(r"\[资料\s*(\d+)\]", result.answer)]
        if evidence and (not cited or any(n < 1 or n > len(evidence) for n in cited)):
            raise HTTPException(502, "answer contains missing or invalid citations")
        if evidence and self.judge:
            with self.span("verification.entailment"):
                if not self.judge(question, result.answer, evidence):
                    raise HTTPException(502, "answer is not supported by evidence")
        output = dict(request_id=result.request_id, answer=result.answer,
            sources=[source.model_dump() for source in result.sources], timings_ms=result.timings_ms,
            retrieval_count=result.retrieval_count, release_id=release_id, cached=False,
            verification="judge_passed" if evidence and self.judge else "citation_structure_only")
        # Recheck current permissions before publishing evidence after long LLM calls.
        if set(allowed) != set(self.index.allowed(principal, release)):
            raise HTTPException(409, "permissions changed; retry the request")
        serialized = json.dumps(output, ensure_ascii=False)
        if self.redis:
            self.redis.setex(cache_key, 300, serialized)
        else:
            with self.cache_lock:
                if len(self.cache) >= 256:
                    self.cache.pop(next(iter(self.cache)))
                self.cache[cache_key] = (time.time() + 300, serialized)
        self.save_turn(principal, session_id, release_id, acl_key, question, output)
        return output

    def save_turn(self, principal, session, release, acl_key, question, output):
        if session:
            with self.db.engine.begin() as connection:
                connection.execute(turns.insert().values(id=uuid.uuid4().hex, tenant=principal.tenant,
                    subject=principal.subject, session_id=session, release_id=release, acl_key=acl_key,
                    payload={"question": question, "answer": output["answer"]}, created=time.time()))
