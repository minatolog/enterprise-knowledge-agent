"""Integration regressions for LangChain adapters and request-local graph state."""

import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

from app.errors import LLMRequestError
from app.langchain_adapters import HybridRAGRetriever, document_to_record
from app.service import RAGService


def record(question):
    return {
        "text": f"证据：{question}", "chunk_id": question,
        "source": "policy.pdf", "relative_path": "data/cnooc/policy.pdf",
        "page_start": 7, "page_end": 8, "section": "第三章",
        "source_url": None, "rerank_score": 0.8, "rrf_score": 0.02,
    }


class WorkflowTests(unittest.TestCase):
    def test_document_adapter_preserves_full_evidence_and_scores(self):
        original = record("条款")
        backend = Mock(return_value=[original])
        retriever = HybridRAGRetriever(backend=backend, k=7, candidate_k=3)
        documents = retriever.invoke("条款")
        backend.assert_called_once_with(question="条款", k=7, candidate_k=7)
        self.assertEqual([document_to_record(doc) for doc in documents], [original])
        self.assertEqual(documents[0].metadata["page_end"], 8)

    def test_concurrent_requests_do_not_share_evidence_or_citations(self):
        def retrieve(question, **kwargs):
            return [record(question)] if question != "empty" else []

        def generate(question, context):
            self.assertIn(f"证据：{question}", context)
            return f"{question} [资料 1]"

        service = RAGService(retriever=retrieve, llm=generate)
        questions = [f"request-{n}" for n in range(12)] + ["empty"]
        with ThreadPoolExecutor(max_workers=4) as pool:
            answers = list(pool.map(service.answer, questions))
        for question, answer in zip(questions[:-1], answers[:-1]):
            self.assertEqual(answer.answer, f"{question} [资料 1]")
            self.assertEqual([source.chunk_id for source in answer.sources], [question])
        self.assertEqual(answers[-1].sources, [])
        self.assertEqual(answers[-1].timings_ms["llm_ms"], 0)

    def test_index_failure_stops_before_retrieval_and_generation(self):
        retriever, llm = Mock(), Mock()
        service = RAGService(
            retriever=retriever, llm=llm,
            index_checker=Mock(side_effect=RuntimeError("index unavailable")),
        )
        with self.assertRaisesRegex(RuntimeError, "index unavailable"):
            service.answer("问题")
        retriever.assert_not_called()
        llm.assert_not_called()

    def test_invalid_generation_never_returns_as_a_successful_graph_result(self):
        for invalid in (None, "", "   ", "LLM API 调用失败：secret"):
            with self.subTest(answer=invalid):
                service = RAGService(
                    retriever=lambda **kwargs: [record("条款")],
                    llm=Mock(return_value=invalid),
                )
                with self.assertRaises(LLMRequestError):
                    service.answer("问题")

    def test_nonempty_request_followed_by_empty_request_has_no_stale_sources(self):
        backend = Mock(side_effect=[[record("first")], []])
        model = Mock(return_value="回答 [资料 1]")
        service = RAGService(retriever=backend, llm=model)
        first = service.answer("有证据")
        second = service.answer("没证据")
        self.assertEqual(len(first.sources), 1)
        self.assertEqual(second.retrieval_results, [])
        self.assertEqual(second.sources, [])
        model.assert_called_once()


if __name__ == "__main__":
    unittest.main()
