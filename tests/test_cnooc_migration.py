import csv
import hashlib
import unittest
from unittest.mock import patch
from pathlib import Path

from document_tracker import detect_changes
from hybrid_retrieval import get_bm25_corpus
from knowledge_config import INDEXED_DOCUMENTS, KNOWLEDGE_BASE, ROOT, selected_paths
from rag import build_chunks
from retrieval import get_collection


class CnoocMigrationTests(unittest.TestCase):
    def test_allowlist_and_original_hashes(self):
        paths = selected_paths()
        self.assertEqual(len(paths), 7)
        self.assertNotIn("data/cnooc/finance/annual_report_2025.pdf", paths)
        self.assertNotIn("data/cnooc/sustainability/esg_report_2025.pdf", paths)
        with (ROOT / "data/cnooc/sources.csv").open(encoding="utf-8-sig", newline="") as handle:
            rows = {row["relative_path"]: row for row in csv.DictReader(handle)}
        self.assertEqual(len(rows), 9)
        for name, path in paths.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), rows[name]["sha256"])

    def test_chunks_have_stable_page_metadata(self):
        chunks = build_chunks()
        self.assertEqual(len(chunks), 194)
        self.assertEqual(len({chunk["chunk_id"] for chunk in chunks}), len(chunks))
        self.assertEqual({chunk["relative_path"] for chunk in chunks}, set(INDEXED_DOCUMENTS))
        for chunk in chunks:
            self.assertTrue(chunk["text"].strip())
            self.assertEqual(chunk["knowledge_base"], KNOWLEDGE_BASE)
            self.assertGreater(chunk["page_start"], 0)
            self.assertEqual(chunk["page_start"], chunk["page_end"])
            self.assertIn(f"::p{chunk['page_start']:04d}::", chunk["chunk_id"])

    def test_bm25_and_vector_use_identical_ids(self):
        collection = get_collection()
        records = collection.get(include=["metadatas"])
        corpus, _ = get_bm25_corpus()
        self.assertEqual(len(records["ids"]), len(corpus), 194)
        self.assertEqual(set(records["ids"]), {item["chunk_id"] for item in corpus})
        self.assertTrue(all(metadata["knowledge_base"] == KNOWLEDGE_BASE for metadata in records["metadatas"]))
        self.assertTrue(all(metadata["relative_path"] in INDEXED_DOCUMENTS for metadata in records["metadatas"]))

    def test_state_is_stable_and_legacy_files_are_outside_data(self):
        changes = detect_changes()
        self.assertEqual(changes["added"], [])
        self.assertEqual(changes["modified"], [])
        self.assertEqual(changes["deleted"], [])
        self.assertEqual(len(changes["unchanged"]), 7)
        for name in ("employee_policy.md", "it_policy.md", "travel_policy.md", "security_policy.txt"):
            self.assertFalse((ROOT / "data" / name).exists())
        self.assertTrue((ROOT / ".index_state/legacy_document_hashes.json").exists())

    def test_missing_selected_document_is_detected_for_cleanup(self):
        paths = selected_paths()
        removed = next(iter(paths))
        with patch("document_tracker.selected_paths", return_value={
            name: path for name, path in paths.items() if name != removed
        }):
            changes = detect_changes()
        self.assertEqual(changes["deleted"], [removed])


if __name__ == "__main__":
    unittest.main()
