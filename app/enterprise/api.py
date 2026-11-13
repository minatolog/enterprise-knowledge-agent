"""Enterprise entry point: uvicorn app.enterprise.api:create_app --factory."""
import json
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.enterprise.auth import Auth, Principal
from app.enterprise.config import Settings
from app.enterprise.db import Database, documents, jobs, releases, versions
from app.enterprise.index import Index
from app.enterprise.runtime import Runtime
from app.enterprise.storage import ObjectStore
from schemas import QueryRequest
from app.errors import ApplicationError


class Query(QueryRequest):
    session_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,64}$")


class ACL(BaseModel):
    groups: list[str] = Field(min_length=1, max_length=100)


class ConnectorRequest(ACL):
    url: str = Field(max_length=2048)


def create_app(settings=None, runtime=None):
    settings = settings or Settings()
    if runtime is None:
        database, objects = Database(settings), ObjectStore(settings)
        runtime = Runtime(settings, database, objects, Index(settings, database, objects))
    auth = Auth(settings)
    app = FastAPI(title="Enterprise RAG", version="0.2.0")
    app.state.runtime = runtime

    def principal(authorization: str | None = Header(default=None)):
        return auth.verify(authorization)

    def admin(user: Principal = Depends(principal)):
        if "admin" not in user.roles:
            raise HTTPException(403, "admin role required")
        return user

    @app.middleware("http")
    async def trace(request: Request, call_next):
        identity = uuid.uuid4().hex
        if request.method in {"POST", "PUT", "PATCH"}:
            parts, length = [], 0
            async for part in request.stream():
                length += len(part)
                if length > settings.max_upload_bytes + 1024 * 1024:
                    return JSONResponse(status_code=413, content={"detail": "request size limit exceeded"})
                parts.append(part)
            request._body = b"".join(parts)
        try:
            with runtime.span("http." + request.method):
                response = await call_next(request)
        except Exception:
            # Never include provider/storage errors or secret-bearing URLs in responses.
            response = JSONResponse(status_code=500, content={"detail": "internal error", "request_id": identity})
        response.headers["X-Request-ID"] = identity
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(ApplicationError)
    async def application_error(request, exc):
        return JSONResponse(status_code=exc.status_code, content={"code": exc.code, "detail": exc.message})

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": "enterprise"}

    @app.get("/ready")
    def ready(_=Depends(admin)):
        try:
            from sqlalchemy import text
            with runtime.db.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            if runtime.redis:
                runtime.redis.ping()
            if runtime.objects.client:
                runtime.objects.client.head_bucket(Bucket=runtime.objects.bucket)
        except Exception:
            raise HTTPException(503, "required backend unavailable")
        return {"status": "ready"}

    @app.get("/metrics")
    def metrics(_=Depends(admin)):
        return Response(runtime.metrics(), media_type="text/plain; version=0.0.4")

    @app.post("/api/v2/query")
    def query(payload: Query, user=Depends(principal)):
        return runtime.query(user, payload.question, payload.top_k, payload.session_id)

    @app.get("/api/v2/sessions/{session_id}")
    def history(session_id: str, user=Depends(principal)):
        release = runtime.db.release(user.tenant)
        allowed = runtime.index.allowed(user, release)
        return {"turns": runtime.history(user, session_id, release["id"] if release else "none", runtime.acl_key(user, allowed))}

    @app.get("/api/v2/documents")
    def list_documents(user=Depends(principal)):
        rows = runtime.db.rows(select(documents).where(documents.c.tenant == user.tenant, documents.c.deleted == 0))
        return [{key: row[key] for key in ("id", "title", "version", "groups")} for row in rows
            if "admin" in user.roles or set(row["groups"]) & set(user.groups)]

    @app.post("/api/v2/documents", status_code=201)
    def upload(title: str = Form(..., max_length=512), groups: str = Form(...),
        document_id: str | None = Form(None), file: UploadFile = File(...), user=Depends(principal)):
        user.editor()
        try:
            acl = ACL(groups=json.loads(groups)).groups
        except (ValueError, TypeError):
            raise HTTPException(422, "groups must be a nonempty JSON string array")
        data = file.file.read(settings.max_upload_bytes + 1)
        row = runtime.upload(user, title, data, Path(file.filename or "").suffix.lower(), acl, document_id)
        return {key: row[key] for key in ("id", "title", "version", "groups")}

    @app.put("/api/v2/documents/{identity}/acl")
    def change_acl(identity: str, payload: ACL, user=Depends(admin)):
        with runtime.index.lock(user.tenant):
            if not runtime.db.document(user.tenant, identity):
                raise HTTPException(404, "document not found")
            with runtime.db.engine.begin() as connection:
                connection.execute(documents.update().where(documents.c.tenant == user.tenant, documents.c.id == identity).values(groups=payload.groups))
        return {"status": "updated"}

    @app.delete("/api/v2/documents/{identity}")
    def delete(identity: str, user=Depends(admin)):
        with runtime.index.lock(user.tenant):
            with runtime.db.engine.begin() as connection:
                outcome = connection.execute(documents.update().where(documents.c.tenant == user.tenant, documents.c.id == identity).values(deleted=1))
            if not outcome.rowcount:
                raise HTTPException(404, "document not found")
        return {"status": "withdrawn"}

    @app.get("/api/v2/documents/{identity}/original")
    def original(identity: str, release_id: str | None = None, user=Depends(principal)):
        row = runtime.db.document(user.tenant, identity)
        if not row or ("admin" not in user.roles and not set(row["groups"]) & set(user.groups)):
            raise HTTPException(404, "document not found")
        release = runtime.db.release(user.tenant)
        if release_id:
            rows = runtime.db.rows(select(releases).where(releases.c.id == release_id, releases.c.tenant == user.tenant))
            release = rows[0] if rows else None
        if not release or identity not in release["manifest"]:
            raise HTTPException(404, "published document not found")
        original_row = release["manifest"][identity]
        return Response(runtime.objects.get(original_row["object_key"]), media_type="application/octet-stream",
            headers={"Content-Disposition": 'attachment; filename="document' + Path(row["object_key"]).suffix + '"'})

    def enqueue(user, identity=None):
        user.editor()
        identity = identity or runtime.db.new_job(user.tenant)
        if settings.eager:
            try:
                runtime.run_job(identity)
            except Exception:
                pass  # Failure is durably visible through the job endpoint.
        else:
            from app.enterprise.queue import create_queue
            create_queue(settings).send_task("enterprise.publish", args=[identity])
        return {"job_id": identity}

    @app.post("/api/v2/index/publish", status_code=202)
    def publish(user=Depends(principal)):
        return enqueue(user)

    @app.get("/api/v2/jobs/{identity}")
    def job(identity: str, user=Depends(principal)):
        user.editor()
        rows = runtime.db.rows(select(jobs).where(jobs.c.tenant == user.tenant, jobs.c.id == identity))
        if not rows:
            raise HTTPException(404, "job not found")
        return rows[0]

    @app.post("/api/v2/jobs/{identity}/retry", status_code=202)
    def retry(identity: str, user=Depends(principal)):
        current = job(identity, user)
        if current["status"] != "failed" or current["attempts"] >= 5:
            raise HTTPException(409, "job cannot be retried")
        return enqueue(user, identity)

    @app.get("/api/v2/index/releases")
    def release_list(user=Depends(admin)):
        rows = runtime.db.rows(select(releases.c.id, releases.c.created).where(releases.c.tenant == user.tenant))
        current = runtime.db.release(user.tenant)
        return {"active": current["id"] if current else None, "releases": rows}

    @app.post("/api/v2/index/rollback/{identity}")
    def rollback(identity: str, user=Depends(admin)):
        try:
            runtime.index.rollback(user.tenant, identity)
        except ValueError:
            raise HTTPException(404, "release not found")
        return {"active": identity}

    @app.post("/api/v2/connectors/sync")
    def sync(payload: ConnectorRequest, user=Depends(admin)):
        from app.enterprise.connectors import fetch_pages
        try:
            rows = fetch_pages(settings, payload.url)
        except Exception:
            raise HTTPException(502, "connector fetch failed; check allowlist and configuration")
        result = runtime.sync_pages(user, payload.url, rows, payload.groups)
        return {"documents": result, **enqueue(user)}

    return app
