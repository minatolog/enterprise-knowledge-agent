import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import ValidationError

import llm
from app.api import create_app
from app.errors import (
    IndexNotReadyError,
    LLMConfigurationError,
    LLMRequestError,
    QuestionValidationError,
    RetrievalError,
)
from app.index_status import ensure_index_ready, list_indexed_documents
from app.service import RAGService
from knowledge_config import (
    DB_PATH,
    DEFAULT_CANDIDATE_K,
    DEFAULT_TOP_K,
    MAX_QUESTION_LENGTH,
    MAX_TOP_K,
    NO_EVIDENCE_ANSWER,
)
from main import run_cli
from schemas import DocumentInfo, QueryRequest


def make_result(
    chunk_id: str = "chunk-1",
    relative_path: str = "data/cnooc/mock.pdf",
    page: int = 1,
    rerank_score: float = 0.9,
) -> dict:
    return {
        "chunk_id": chunk_id,
        "text": "这是用于测试的证据文本。",
        "source": Path(relative_path).name,
        "relative_path": relative_path,
        "knowledge_base": "cnooc",
        "page_start": page,
        "page_end": page,
        "section": "",
        "source_url": "https://example.invalid/mock.pdf",
        "rerank_score": rerank_score,
    }


class FakeRetriever:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def __call__(self, question: str, k: int, candidate_k: int):
        self.calls.append({"question": question, "k": k, "candidate_k": candidate_k})
        return self.results


class RaisingRetriever:
    def __call__(self, question: str, k: int, candidate_k: int):
        raise RuntimeError("retrieval boom")


class FakeLLM:
    def __init__(self, answer: str):
        self.answer = answer
        self.calls = []

    def __call__(self, question: str, context: str) -> str:
        self.calls.append({"question": question, "context": context})
        return self.answer


class RaisingLLM:
    def __init__(self, error: Exception):
        self.error = error
        self.calls = []

    def __call__(self, question: str, context: str) -> str:
        self.calls.append({"question": question, "context": context})
        raise self.error


def make_service(results=None, answer="答案 [资料 1]", llm_impl=None, index_checker=None):
    results = [make_result()] if results is None else results
    retriever = FakeRetriever(results)
    llm_impl = llm_impl or FakeLLM(answer)
    service = RAGService(
        retriever=retriever,
        llm=llm_impl,
        index_checker=index_checker or (lambda: None),
    )
    return service, retriever, llm_impl


class RAGServiceTests(unittest.TestCase):
    def test_returns_answer_and_only_cited_sources_from_current_retrieval(self):
        results = [
            make_result(chunk_id="chunk-a", relative_path="data/cnooc/a.pdf", page=1),
            make_result(
                chunk_id="chunk-b",
                relative_path="data/cnooc/b.pdf",
                page=2,
                rerank_score=0.8,
            ),
        ]
        service, retriever, llm_impl = make_service(
            results,
            answer="答案 [资料 2] [资料 9]",
        )

        result = service.answer("问题", top_k=3, request_id="req-service")

        self.assertEqual(result.request_id, "req-service")
        self.assertEqual(result.answer, "答案 [资料 2] [资料 9]")
        self.assertEqual([item.chunk_id for item in result.sources], ["chunk-b"])
        self.assertEqual(result.sources[0].relative_path, "data/cnooc/b.pdf")
        self.assertEqual(result.legacy_sources, ["data/cnooc/b.pdf，第2页"])
        self.assertEqual(result.rerank_score, 0.9)
        self.assertEqual(result.retrieval_count, 2)
        self.assertEqual(retriever.calls[0]["k"], 3)
        self.assertEqual(retriever.calls[0]["candidate_k"], DEFAULT_CANDIDATE_K)
        self.assertEqual(llm_impl.calls[0]["question"], "问题")

    def test_default_top_k_and_candidate_come_from_config(self):
        service, retriever, _ = make_service()
        service.answer("默认问题")

        self.assertEqual(retriever.calls[0]["k"], DEFAULT_TOP_K)
        self.assertEqual(retriever.calls[0]["candidate_k"], DEFAULT_CANDIDATE_K)

    def test_top_k_above_candidate_expands_candidate_pool(self):
        service, retriever, _ = make_service()
        service.answer("更大 top_k", top_k=MAX_TOP_K)

        self.assertEqual(retriever.calls[0]["k"], MAX_TOP_K)
        self.assertEqual(
            retriever.calls[0]["candidate_k"],
            max(DEFAULT_CANDIDATE_K, MAX_TOP_K),
        )

    def test_no_results_returns_refusal_without_calling_llm(self):
        service, _, llm_impl = make_service([], answer="不应被调用")

        result = service.answer("无答案问题")

        self.assertEqual(result.answer, NO_EVIDENCE_ANSWER)
        self.assertEqual(result.sources, [])
        self.assertEqual(result.legacy_sources, [])
        self.assertEqual(result.retrieval_count, 0)
        self.assertIsNone(result.rerank_score)
        self.assertEqual(llm_impl.calls, [])

    def test_question_and_top_k_validation(self):
        service, _, _ = make_service()

        for question in ("", "   ", "x" * (MAX_QUESTION_LENGTH + 1)):
            with self.subTest(question=question[:10]):
                with self.assertRaises(QuestionValidationError):
                    service.answer(question)

        for top_k in (0, MAX_TOP_K + 1, True):
            with self.subTest(top_k=top_k):
                with self.assertRaises(QuestionValidationError):
                    service.answer("问题", top_k=top_k)

    def test_llm_configuration_error_propagates(self):
        service, _, _ = make_service(
            llm_impl=RaisingLLM(LLMConfigurationError())
        )
        with self.assertRaises(LLMConfigurationError):
            service.answer("问题")

    def test_llm_request_error_is_normalized(self):
        service, _, _ = make_service(llm_impl=RaisingLLM(LLMRequestError("internal")))
        with self.assertRaises(LLMRequestError) as context:
            service.answer("问题")
        self.assertNotIn("internal", str(context.exception))

    def test_retrieval_error_is_wrapped(self):
        service = RAGService(
            retriever=RaisingRetriever(),
            llm=FakeLLM("答案"),
            index_checker=lambda: None,
        )
        with self.assertRaises(RetrievalError):
            service.answer("问题")

    def test_on_retrieval_callback_receives_same_results(self):
        results = [make_result()]
        service, _, _ = make_service(results)
        captured = []

        service.answer("问题", on_retrieval=captured.append)

        self.assertEqual(captured, [results])


class QueryRequestTests(unittest.TestCase):
    def test_strips_question_and_uses_default_top_k(self):
        request = QueryRequest(question="  测试问题  ")
        self.assertEqual(request.question, "测试问题")
        self.assertEqual(request.top_k, DEFAULT_TOP_K)

    def test_rejects_invalid_question_and_top_k(self):
        cases = [
            {"question": ""},
            {"question": "   "},
            {"question": "x" * (MAX_QUESTION_LENGTH + 1)},
            {"question": "问题", "top_k": 0},
            {"question": "问题", "top_k": MAX_TOP_K + 1},
            {"question": "问题", "top_k": True},
            {"question": "问题", "top_k": "2"},
        ]
        for payload in cases:
            with self.subTest(payload=str(payload)[:30]):
                with self.assertRaises(ValidationError):
                    QueryRequest(**payload)


class ConfigLoadingTests(unittest.TestCase):
    def test_dotenv_settings_are_loaded_before_config_is_read(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            shutil.copyfile(
                Path(__file__).resolve().parents[1] / "knowledge_config.py",
                temp_path / "knowledge_config.py",
            )
            (temp_path / ".env").write_text(
                "RAG_TOP_K=7\nDEEPSEEK_MODEL=test-model\n",
                encoding="utf-8",
            )
            env = os.environ.copy()
            env.pop("RAG_TOP_K", None)
            env.pop("DEEPSEEK_MODEL", None)
            env["PYTHONPATH"] = str(temp_path)
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import knowledge_config as c; print(c.DEFAULT_TOP_K, c.LLM_MODEL)",
                ],
                cwd=temp_path,
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertEqual(result.stdout.strip(), "7 test-model")


class APITests(unittest.TestCase):
    def test_local_chat_page_and_assets_are_served_without_index_or_key(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}, clear=False):
            client = TestClient(create_app())
            page = client.get("/legacy")
            script = client.get("/static/app.js")
            stylesheet = client.get("/static/styles.css")

        self.assertEqual(page.status_code, 200)
        self.assertIn("资料问答", page.text)
        self.assertIn('id="query-form"', page.text)
        self.assertEqual(script.status_code, 200)
        self.assertIn('fetch("/api/v1/query"', script.text)
        self.assertEqual(stylesheet.status_code, 200)
        self.assertIn(".conversation", stylesheet.text)

    def test_health_does_not_require_key_or_index(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}, clear=False):
            client = TestClient(create_app())
            response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_query_returns_request_id_and_structured_sources(self):
        results = [
            make_result(chunk_id="chunk-a", relative_path="data/cnooc/a.pdf", page=1),
            make_result(
                chunk_id="chunk-b",
                relative_path="data/cnooc/b.pdf",
                page=2,
                rerank_score=0.8,
            ),
        ]
        service, _, _ = make_service(results, answer="答案 [资料 1] [资料 2]")
        client = TestClient(create_app(service=service))

        response = client.post(
            "/api/v1/query",
            json={"question": "问题", "top_k": 2},
            headers={"X-Request-ID": "req-api"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Request-ID"], "req-api")
        body = response.json()
        self.assertEqual(body["request_id"], "req-api")
        self.assertEqual(len(body["sources"]), 2)
        self.assertEqual(
            [item["chunk_id"] for item in body["sources"]],
            ["chunk-a", "chunk-b"],
        )
        self.assertEqual(body["sources"][0]["relative_path"], "data/cnooc/a.pdf")
        self.assertEqual(body["retrieval_count"], 2)
        self.assertIn("retrieval_ms", body["timings_ms"])

    def test_query_no_results_returns_refusal(self):
        service, _, llm_impl = make_service([], answer="不应被调用")
        client = TestClient(create_app(service=service))

        response = client.post("/api/v1/query", json={"question": "无答案"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["answer"], NO_EVIDENCE_ANSWER)
        self.assertEqual(body["sources"], [])
        self.assertEqual(body["retrieval_count"], 0)
        self.assertEqual(llm_impl.calls, [])

    def test_query_validation_errors_include_request_id(self):
        service, _, _ = make_service()
        client = TestClient(create_app(service=service))
        cases = [
            {},
            {"question": ""},
            {"question": "   "},
            {"question": "x" * (MAX_QUESTION_LENGTH + 1)},
            {"question": "问题", "top_k": 0},
            {"question": "问题", "top_k": MAX_TOP_K + 1},
            {"question": "问题", "top_k": True},
            {"question": "问题", "top_k": "2"},
        ]

        for payload in cases:
            with self.subTest(payload=str(payload)[:30]):
                response = client.post(
                    "/api/v1/query",
                    json=payload,
                    headers={"X-Request-ID": "req-invalid"},
                )
                self.assertEqual(response.status_code, 422)
                body = response.json()
                self.assertEqual(body["code"], "INVALID_REQUEST")
                self.assertEqual(body["request_id"], "req-invalid")
                self.assertEqual(response.headers["X-Request-ID"], "req-invalid")

    def test_query_llm_failure_returns_stable_error(self):
        service, _, _ = make_service(
            llm_impl=RaisingLLM(LLMRequestError())
        )
        client = TestClient(create_app(service=service))

        response = client.post(
            "/api/v1/query",
            json={"question": "问题"},
            headers={"X-Request-ID": "req-llm"},
        )

        self.assertEqual(response.status_code, 502)
        body = response.json()
        self.assertEqual(body["code"], "LLM_REQUEST_FAILED")
        self.assertEqual(body["request_id"], "req-llm")

    def test_query_missing_key_returns_503(self):
        service, _, _ = make_service(
            llm_impl=RaisingLLM(LLMConfigurationError())
        )
        client = TestClient(create_app(service=service))

        response = client.post("/api/v1/query", json={"question": "问题"})

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "LLM_NOT_CONFIGURED")

    def test_query_retrieval_failure_returns_503(self):
        service = RAGService(
            retriever=RaisingRetriever(),
            llm=FakeLLM("答案"),
            index_checker=lambda: None,
        )
        client = TestClient(create_app(service=service))

        response = client.post("/api/v1/query", json={"question": "问题"})

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "RETRIEVAL_FAILED")

    def test_query_missing_index_returns_503(self):
        service = RAGService(
            retriever=FakeRetriever([make_result()]),
            llm=FakeLLM("答案"),
            index_checker=lambda: (_ for _ in ()).throw(IndexNotReadyError()),
        )
        client = TestClient(create_app(service=service))

        response = client.post("/api/v1/query", json={"question": "问题"})

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "INDEX_NOT_READY")

    def test_documents_missing_index_returns_503(self):
        service, _, _ = make_service()
        app = create_app(
            service=service,
            documents_provider=lambda: (_ for _ in ()).throw(IndexNotReadyError()),
        )
        client = TestClient(app)

        response = client.get("/api/v1/documents")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "INDEX_NOT_READY")

    def test_documents_uses_injected_provider_not_whitelist(self):
        service, _, _ = make_service()
        documents = [
            DocumentInfo(
                source="mock.pdf",
                relative_path="mock/only.pdf",
                chunk_count=2,
                page_start=1,
                page_end=2,
                source_url=None,
                knowledge_base="mock",
            )
        ]
        app = create_app(
            service=service,
            documents_provider=lambda: (documents, 2),
        )
        client = TestClient(app)

        response = client.get("/api/v1/documents")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["indexed_document_count"], 1)
        self.assertEqual(body["indexed_chunk_count"], 2)
        self.assertEqual(body["documents"][0]["relative_path"], "mock/only.pdf")

    @unittest.skipUnless(
        (DB_PATH / "chroma.sqlite3").is_file(),
        "local Chroma index not available",
    )
    def test_documents_real_index_is_read_only(self):
        service, _, _ = make_service()
        client = TestClient(create_app(service=service))

        response = client.get("/api/v1/documents")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertGreater(body["indexed_chunk_count"], 0)
        self.assertGreater(len(body["documents"]), 0)
        self.assertEqual(
            sum(item["chunk_count"] for item in body["documents"]),
            body["indexed_chunk_count"],
        )
        self.assertNotIn("text", body["documents"][0])

    @unittest.skipUnless(
        (DB_PATH / "chroma.sqlite3").is_file(),
        "local Chroma index not available",
    )
    def test_list_indexed_documents_real_index(self):
        documents, total_chunks = list_indexed_documents()

        self.assertGreater(total_chunks, 0)
        self.assertGreater(len(documents), 0)
        self.assertEqual(sum(item.chunk_count for item in documents), total_chunks)
        self.assertTrue(all(item.chunk_count > 0 for item in documents))

    @unittest.skipUnless(
        (DB_PATH / "chroma.sqlite3").is_file(),
        "local Chroma index not available",
    )
    def test_ensure_index_ready_real_index(self):
        ensure_index_ready()

    def test_list_indexed_documents_missing_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir)
            with self.assertRaises(IndexNotReadyError):
                ensure_index_ready(db_path=missing)
            with self.assertRaises(IndexNotReadyError):
                list_indexed_documents(db_path=missing)


class LLMTests(unittest.TestCase):
    def test_missing_key_raises_configuration_error_without_network(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}, clear=False):
            with self.assertRaises(LLMConfigurationError):
                llm.get_client()

    def test_request_failure_is_wrapped_without_network(self):
        class FakeResponses:
            def create(self, **kwargs):
                raise RuntimeError("boom")

        class FakeClient:
            responses = FakeResponses()

        with patch("llm.get_client", return_value=FakeClient()):
            with self.assertRaises(LLMRequestError):
                llm.answer_with_context("问题", "上下文")


class CLITests(unittest.TestCase):
    def test_cli_uses_same_service_and_preserves_legacy_sources(self):
        service, retriever, llm_impl = make_service(answer="答案 [资料 1]")
        output = []

        response = run_cli(
            service=service,
            input_func=lambda _: "问题",
            output_func=output.append,
        )

        self.assertIsNotNone(response)
        self.assertEqual(response.answer, "答案 [资料 1]")
        self.assertEqual(response.sources, ["data/cnooc/mock.pdf，第1页"])
        self.assertEqual(retriever.calls[0]["k"], DEFAULT_TOP_K)
        self.assertEqual(retriever.calls[0]["candidate_k"], DEFAULT_CANDIDATE_K)
        self.assertEqual(len(llm_impl.calls), 1)
        self.assertTrue(any("Retrieval Results" in line for line in output))
        self.assertTrue(any("最终结果" in line for line in output))

    def test_cli_empty_question(self):
        service, retriever, _ = make_service()
        output = []

        response = run_cli(
            service=service,
            input_func=lambda _: "   ",
            output_func=output.append,
        )

        self.assertIsNone(response)
        self.assertIn("问题不能为空。", output)
        self.assertEqual(retriever.calls, [])

    def test_cli_error_is_reported_without_json(self):
        service, _, _ = make_service(
            llm_impl=RaisingLLM(LLMRequestError())
        )
        output = []

        response = run_cli(
            service=service,
            input_func=lambda _: "问题",
            output_func=output.append,
        )

        self.assertIsNone(response)
        self.assertTrue(any("程序运行失败" in line for line in output))


if __name__ == "__main__":
    unittest.main()
