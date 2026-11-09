import importlib.util
import json
import re
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from ingestion import load_document
from knowledge_config import DB_PATH, INDEXED_DOCUMENTS, KNOWLEDGE_BASE, ROOT
from rag import chunk_document

DATASET_PATH = ROOT / "eval" / "cnooc_eval_v1.json"


def load_eval_module():
    path = ROOT / "eval" / "run_cnooc_eval.py"
    spec = importlib.util.spec_from_file_location("cnooc_eval_runner", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


class CnoocDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        cls.questions = cls.dataset["questions"]
        cls.answerable = [
            q for q in cls.questions if not q["requires_abstention"]
        ]
        cls.abstention = [
            q for q in cls.questions if q["requires_abstention"]
        ]

    def test_dataset_counts_ids_and_required_fields(self):
        self.assertEqual(len(self.questions), 31)
        self.assertEqual(len(self.answerable), 26)
        self.assertEqual(len(self.abstention), 5)
        ids = [q["question_id"] for q in self.questions]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(
            {q["review_status"] for q in self.questions},
            {"ai_draft_source_checked"},
        )
        for question in self.answerable:
            self.assertTrue(question["expected_document_ids"])
            self.assertTrue(question["expected_pages"])
            self.assertTrue(question["expected_chunk_ids"])
            self.assertTrue(question["evidence"])
            self.assertTrue(question["answer_reference"])
            self.assertFalse(question["requires_abstention"])
        for question in self.abstention:
            self.assertEqual(question["expected_document_ids"], [])
            self.assertEqual(question["expected_pages"], [])
            self.assertEqual(question["expected_chunk_ids"], [])
            self.assertEqual(question["evidence"], [])
            self.assertTrue(question["abstention_basis"])
            self.assertTrue(question["requires_abstention"])

    def test_every_quote_matches_its_pdf_page_and_expected_chunk(self):
        chunks = {}
        pages = {}
        for document_id in INDEXED_DOCUMENTS:
            document = load_document(ROOT / document_id)
            pages[document_id] = {
                page["page_number"]: page["text"] for page in document["pages"]
            }
            for chunk in chunk_document(document):
                chunks[chunk["chunk_id"]] = chunk

        for question in self.answerable:
            expected_documents = set(question["expected_document_ids"])
            self.assertEqual(
                expected_documents,
                {chunk_id.split("::")[0] for chunk_id in question["expected_chunk_ids"]},
            )
            for evidence in question["evidence"]:
                document_id = evidence["document_id"]
                page = evidence["page"]
                quote = compact(evidence["quote"])
                self.assertIn(document_id, expected_documents)
                self.assertIn(page, question["expected_pages"])
                self.assertIn(quote, compact(pages[document_id][page]))
                matching = [
                    chunk_id
                    for chunk_id in question["expected_chunk_ids"]
                    if chunk_id in chunks
                    and quote in compact(chunks[chunk_id]["text"])
                ]
                self.assertTrue(
                    matching,
                    f"{question['question_id']} 证据不在声明的 Chunk 中：{quote[:40]}",
                )

    def test_expected_chunk_ids_exist_in_current_index_read_only(self):
        sqlite_path = DB_PATH / "chroma.sqlite3"
        self.assertTrue(sqlite_path.is_file())
        connection = sqlite3.connect(
            sqlite_path.resolve().as_uri() + "?mode=ro&immutable=1",
            uri=True,
        )
        try:
            indexed = {
                row[0]
                for row in connection.execute("SELECT embedding_id FROM embeddings")
            }
        finally:
            connection.close()
        expected = {
            chunk_id
            for question in self.answerable
            for chunk_id in question["expected_chunk_ids"]
        }
        self.assertEqual(expected - indexed, set())

    def test_vector_and_bm25_ids_match_on_isolated_copy(self):
        import hybrid_retrieval
        import retrieval

        original_db_path = retrieval.DB_PATH
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                copied_db = Path(temp_dir) / "chroma_db"
                shutil.copytree(DB_PATH, copied_db)
                retrieval.DB_PATH = copied_db
                retrieval._collection = None
                hybrid_retrieval._corpus = None
                hybrid_retrieval._bm25 = None

                collection = retrieval.get_collection()
                records = collection.get(include=["metadatas"])
                corpus, _ = hybrid_retrieval.get_bm25_corpus()

                self.assertEqual(len(records["ids"]), len(corpus))
                self.assertEqual(
                    set(records["ids"]),
                    {item["chunk_id"] for item in corpus},
                )
                self.assertTrue(all(
                    metadata["knowledge_base"] == KNOWLEDGE_BASE
                    for metadata in records["metadatas"]
                ))
                self.assertTrue(all(
                    metadata["relative_path"] in INDEXED_DOCUMENTS
                    for metadata in records["metadatas"]
                ))
        finally:
            retrieval.DB_PATH = original_db_path
            retrieval._collection = None
            hybrid_retrieval._corpus = None
            hybrid_retrieval._bm25 = None


class CnoocMetricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = load_eval_module()

    @staticmethod
    def result(chunk_id, score=0.0):
        return {
            "chunk_id": chunk_id,
            "relative_path": "data/cnooc/mock.pdf",
            "page_start": 1,
            "page_end": 1,
            "distance": score,
        }

    def test_hit_recall_mrr_and_abstention_exclusion(self):
        questions = [
            {
                "question_id": "Q1",
                "question": "问题一",
                "category": "clause",
                "difficulty": "easy",
                "expected_chunk_ids": ["a", "b"],
                "expected_pages": [1],
                "expected_document_ids": ["data/cnooc/mock.pdf"],
                "requires_abstention": False,
            },
            {
                "question_id": "Q2",
                "question": "问题二",
                "category": "clause",
                "difficulty": "easy",
                "expected_chunk_ids": ["c"],
                "expected_pages": [1],
                "expected_document_ids": ["data/cnooc/mock.pdf"],
                "requires_abstention": False,
            },
            {
                "question_id": "U1",
                "question": "无答案",
                "category": "abstention",
                "difficulty": "easy",
                "expected_chunk_ids": [],
                "expected_pages": [],
                "expected_document_ids": [],
                "requires_abstention": True,
            },
        ]
        q1_results = [
            self.result("x"),
            self.result("a"),
            self.result("b"),
        ] + [self.result(f"x{i}") for i in range(3, 11)]
        q2_results = [self.result(f"y{i}") for i in range(1, 11)]
        q3_results = [self.result(f"z{i}") for i in range(1, 11)]

        def fake_retrieve(question, k):
            self.assertEqual(k, 10)
            return {
                "问题一": q1_results,
                "问题二": q2_results,
                "无答案": q3_results,
            }[question]

        result = self.runner.evaluate_method("dense", fake_retrieve, questions)
        summary = self.runner.summarize(result, 2)
        q1, q2, q3 = result["records"]

        self.assertEqual(q1["first_relevant_rank"], 2)
        self.assertFalse(q1["hit_at_1"])
        self.assertTrue(q1["hit_at_3"])
        self.assertEqual(q1["recall_at_5"], 1.0)
        self.assertEqual(q1["recall_at_10"], 1.0)
        self.assertIsNone(q1["failure_reason"])

        self.assertIsNone(q2["first_relevant_rank"])
        self.assertFalse(q2["hit_at_3"])
        self.assertEqual(q2["recall_at_5"], 0.0)
        self.assertEqual(q2["recall_at_10"], 0.0)
        self.assertEqual(q2["failure_reason"], "no_expected_chunk_in_top_10")

        self.assertEqual(q3["group"], "abstention")
        self.assertIsNone(q3["recall_at_5"])
        self.assertIsNone(q3["recall_at_10"])
        self.assertIsNone(q3["failure_reason"])

        self.assertEqual(summary["answerable_denominator"], 2)
        self.assertEqual(summary["hit_at_1"], 0.0)
        self.assertEqual(summary["hit_at_3"], 0.5)
        self.assertEqual(summary["recall_at_5"], 0.5)
        self.assertEqual(summary["recall_at_10"], 0.5)
        self.assertEqual(summary["mrr_at_10"], 0.25)


if __name__ == "__main__":
    unittest.main()
