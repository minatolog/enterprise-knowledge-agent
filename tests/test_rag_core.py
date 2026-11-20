"""Unit tests for the shared retrieval core (no models, no index, no network)."""

import unittest

from rag_core.chunking import page_chunks, search_text, structured_chunks
from rag_core.refusal import passes_evidence_gate
from rag_core.search import BM25Index, Reranker, hybrid_search, reciprocal_rank_fusion
from rag_core.textnorm import compact, normalize

CHARTER = [
    {"page_number": 1, "text": "中國海洋石油有限公司\n審核委員會章程\n宗旨\n1. 審核委員會的宗旨是協助董事會履行職責。\n組織結構\n2. 審核委員會成員由董事會不時任命，由不少於三名非執\n行董事組成。\n1"},
    {"page_number": 2, "text": "中國海洋石油有限公司\n會議\n3. 審核委員會每季度至少召開一次會議。除緊急情況外，所有會議文件需在每次開會前\n至少三天發送給全體成員。\n2"},
    {"page_number": 3, "text": "中國海洋石油有限公司\n4. 每次會議至少應有三分之二以上成員參加。\n3"},
    {"page_number": 4, "text": "中國海洋石油有限公司\n報告\n5. 主席應向董事會匯報。\n4"},
]


class TextNormalizationTests(unittest.TestCase):
    def test_traditional_to_simplified_and_cjk_spacing(self):
        self.assertEqual(normalize("本公司的名稱為 中國海洋石油有限公司"), "本公司的名称为中国海洋石油有限公司")
        self.assertEqual(normalize("戰略與可持續發展 委員會"), "战略与可持续发展委员会")

    def test_compact_matches_across_scripts(self):
        self.assertIn(compact("委员会每季度至少召开一次会议"), compact("審核委員會每季度至少 召開一次會議。"))


class ChunkingTests(unittest.TestCase):
    def test_structured_chunks_follow_clauses_and_drop_running_headers(self):
        chunks = structured_chunks(CHARTER, relative_path="doc.pdf", target_chars=60)
        joined = "\n".join(chunk["text"] for chunk in chunks)
        self.assertNotIn("中國海洋石油有限公司\n", joined.replace("審核委員會章程", ""))
        self.assertTrue(all(chunk["chunk_id"].startswith(f"doc.pdf::p{chunk['page_start']:04d}::s") for chunk in chunks))
        # The soft-wrapped clause is glued back together.
        self.assertTrue(any("不少於三名非執行董事組成" in chunk["text"] for chunk in chunks))
        meeting = next(chunk for chunk in chunks if "每季度" in chunk["text"])
        self.assertIn("會議", meeting["section"])
        self.assertIn("至少三天發送", meeting["text"])

    def test_clause_can_cross_pages_into_one_chunk(self):
        chunks = structured_chunks(CHARTER, relative_path="doc.pdf", target_chars=600, min_chars=1000)
        crossing = [chunk for chunk in chunks if chunk["page_end"] > chunk["page_start"]]
        self.assertTrue(crossing)

    def test_single_short_line_document_is_kept(self):
        chunks = structured_chunks([{"page_number": 1, "text": "finance confidential"}], relative_path="x")
        self.assertEqual([chunk["text"] for chunk in chunks], ["finance confidential"])

    def test_long_clause_is_split_on_sentences(self):
        text = "1. " + "。".join("第%d句内容较长需要切分" % i for i in range(200)) + "。"
        chunks = structured_chunks([{"page_number": 1, "text": text}], relative_path="x", target_chars=300, max_chars=300)
        self.assertGreater(len(chunks), 3)
        self.assertTrue(all(len(chunk["text"].replace("\n", "")) <= 300 for chunk in chunks))

    def test_page_chunks_keep_v1_ids(self):
        chunks = page_chunks(CHARTER, relative_path="doc.pdf")
        self.assertEqual(chunks[0]["chunk_id"], "doc.pdf::p0001::c0001")
        self.assertTrue(all(chunk["page_start"] == chunk["page_end"] for chunk in chunks))

    def test_search_text_adds_title_and_section_in_simplified_form(self):
        text = search_text({"title": "審核委員會章程", "section": "會議", "text": "每季度至少召開一次會議"})
        self.assertTrue(text.startswith("审核委员会章程 · 会议"))


class FakeCrossEncoder:
    def predict(self, pairs):
        return [1.0 if "会议" in document else 0.1 for _, document in pairs]


def record(chunk_id, text, document_id="d1"):
    return {"chunk_id": chunk_id, "text": text, "document_id": document_id, "title": "", "section": ""}


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.records = [
            record("a", "審核委員會每季度至少召開一次會議"),
            record("b", "員工入職時須簽署保密協議"),
            record("c", "薪酬委員會的組成", document_id="d2"),
        ]

    def test_bm25_matches_simplified_query_against_traditional_text(self):
        index = BM25Index(self.records)
        self.assertEqual(index.search("委员会多久召开会议", 3)[0]["chunk_id"], "a")

    def test_bm25_acl_filter_is_applied_before_ranking(self):
        index = BM25Index(self.records)
        results = index.search("委员会", 3, allowed=lambda item: item["document_id"] == "d2")
        self.assertEqual([item["chunk_id"] for item in results], ["c"])

    def test_rrf_merges_and_orders(self):
        fused = reciprocal_rank_fusion([self.records[0], self.records[1]], [self.records[1], self.records[2]])
        self.assertEqual([item["chunk_id"] for item in fused], ["b", "a", "c"])
        self.assertAlmostEqual(fused[0]["rrf_score"], 1 / 62 + 1 / 61)

    def test_hybrid_search_uses_candidate_budget_and_reranks(self):
        seen = {}

        def dense(question, budget):
            seen["dense"] = budget
            return [self.records[1], self.records[0]]

        def sparse(question, budget):
            seen["sparse"] = budget
            return [self.records[2]]

        results = hybrid_search("会议", dense=dense, sparse=sparse,
                                reranker=Reranker("fake", model=FakeCrossEncoder()), k=2, candidate_k=20)
        self.assertEqual(seen, {"dense": 20, "sparse": 20})
        self.assertEqual(results[0]["chunk_id"], "a")
        self.assertEqual(len(results), 2)
        self.assertIn("rerank_score", results[0])


class EvidenceGateTests(unittest.TestCase):
    def test_gate(self):
        self.assertFalse(passes_evidence_gate([], 0.1))
        self.assertFalse(passes_evidence_gate([{"rerank_score": 0.05}], 0.1))
        self.assertTrue(passes_evidence_gate([{"rerank_score": 0.1}], 0.1))
        self.assertTrue(passes_evidence_gate([{"rerank_score": 0.0}], 0.0))
        self.assertTrue(passes_evidence_gate([{"text": "no score"}], 0.5))


if __name__ == "__main__":
    unittest.main()
