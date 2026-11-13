"""Minimal FastAPI application for the local RAG service."""

from __future__ import annotations

import logging
import re
import time
import uuid
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.errors import ApplicationError
from app.index_status import list_indexed_documents
from app.logging_config import configure_logging
from app.service import RAGService
from knowledge_config import API_TITLE, API_VERSION, COLLECTION_NAME
from schemas import (
    DocumentInfo,
    DocumentsResponse,
    ErrorResponse,
    HealthResponse,
    QueryRequest,
    QueryResponse,
)

logger = logging.getLogger(__name__)
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_WEB_DIR = Path(__file__).resolve().parent / "web"
_STUDIO_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"


def _get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", uuid.uuid4().hex)


def _error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    request_id = _get_request_id(request)
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            code=code,
            message=message,
            request_id=request_id,
        ).model_dump(),
        headers={"X-Request-ID": request_id},
    )


def create_app(
    service: RAGService | None = None,
    documents_provider: Callable[[], tuple[list[DocumentInfo], int]] | None = None,
) -> FastAPI:
    configure_logging()
    app = FastAPI(title=API_TITLE, version=API_VERSION)
    app.mount("/static", StaticFiles(directory=_WEB_DIR), name="static")
    if (_STUDIO_DIR / "index.html").is_file():
        app.mount("/studio", StaticFiles(directory=_STUDIO_DIR, html=True), name="studio")
    rag_service = service or RAGService()
    get_documents = documents_provider or list_indexed_documents

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        incoming = request.headers.get("X-Request-ID", "")
        request_id = incoming if _REQUEST_ID_PATTERN.fullmatch(incoming) else uuid.uuid4().hex
        request.state.request_id = request_id
        started = time.perf_counter()
        logger.info(
            "http_start method=%s path=%s request_id=%s",
            request.method,
            request.url.path,
            request_id,
        )
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.exception(
                "http_unhandled request_id=%s error_type=%s",
                request_id,
                type(exc).__name__,
            )
            response = _error_response(request, 500, "INTERNAL_ERROR", "服务内部错误")
        duration_ms = round((time.perf_counter() - started) * 1000, 1)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "http_end method=%s path=%s status=%s duration_ms=%s request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response

    @app.exception_handler(ApplicationError)
    async def handle_application_error(request: Request, exc: ApplicationError):
        logger.warning(
            "http_error request_id=%s code=%s status=%s",
            _get_request_id(request),
            exc.code,
            exc.status_code,
        )
        return _error_response(request, exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        logger.info(
            "http_validation_error request_id=%s errors=%s",
            _get_request_id(request),
            len(exc.errors()),
        )
        return _error_response(request, 422, "INVALID_REQUEST", "请求参数不合法")

    @app.exception_handler(HTTPException)
    async def handle_http_error(request: Request, exc: HTTPException):
        message = exc.detail if isinstance(exc.detail, str) else "请求失败"
        return _error_response(request, exc.status_code, "HTTP_ERROR", message)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        logger.exception("http_unexpected request_id=%s", _get_request_id(request))
        return _error_response(request, 500, "INTERNAL_ERROR", "服务内部错误")

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get("/", include_in_schema=False)
    def home() -> FileResponse:
        if (_STUDIO_DIR / "index.html").is_file():
            return FileResponse(_STUDIO_DIR / "index.html")
        return FileResponse(_WEB_DIR / "index.html")

    @app.get("/legacy", include_in_schema=False)
    def legacy_home() -> FileResponse:
        return FileResponse(_WEB_DIR / "index.html")

    @app.post("/api/v1/query", response_model=QueryResponse)
    def query(payload: QueryRequest, request: Request) -> QueryResponse:
        result = rag_service.answer(
            payload.question,
            top_k=payload.top_k,
            request_id=_get_request_id(request),
        )
        return QueryResponse(
            request_id=result.request_id,
            answer=result.answer,
            sources=result.sources,
            rerank_score=result.rerank_score,
            retrieval_count=result.retrieval_count,
            timings_ms=result.timings_ms,
        )

    @app.get("/api/v1/documents", response_model=DocumentsResponse)
    def documents(request: Request) -> DocumentsResponse:
        document_list, chunk_count = get_documents()
        return DocumentsResponse(
            request_id=_get_request_id(request),
            collection=COLLECTION_NAME,
            indexed_document_count=len(document_list),
            indexed_chunk_count=chunk_count,
            documents=document_list,
        )

    return app


app = create_app()
