import csv
import logging
import tempfile
import unittest
from pathlib import Path

from docx import Document
from pypdf import PdfWriter

from ingestion import load_all_documents, load_document, load_document_tree, load_pdf


ROOT = Path(__file__).resolve().parents[1]
logging.getLogger("pypdf").setLevel(logging.ERROR)


class IngestionTests(unittest.TestCase):
    def test_default_scope_stays_shallow_and_explicit_scope_is_recursive(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "old.md").write_text("## Old\nold text", encoding="utf-8")
            nested = root / "company" / "governance"
            nested.mkdir(parents=True)
            (nested / "policy.txt").write_text("中文制度", encoding="utf-8")
            (root / "company" / "policy_alias.txt").symlink_to(nested / "policy.txt")
            (nested / "sources.csv").write_text("not knowledge", encoding="utf-8")

            self.assertEqual([doc["source"] for doc in load_all_documents(root)], ["old.md"])
            self.assertEqual(
                [doc["source"] for doc in load_document_tree(root / "company")],
                ["policy.txt"],
            )

    def test_old_text_and_docx_readers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "policy.md").write_text("## 标题\n内容", encoding="utf-8")
            (root / "policy.txt").write_text("纯文本", encoding="utf-8")
            word = Document()
            word.add_paragraph("Word 内容")
            word.save(root / "policy.docx")

            self.assertIn("内容", load_document(root / "policy.md")["text"])
            self.assertEqual(load_document(root / "policy.txt")["text"], "纯文本")
            self.assertEqual(load_document(root / "policy.docx")["text"], "Word 内容")

    def test_bad_pdf_reports_failure_without_stopping_batch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            writer = PdfWriter()
            writer.add_blank_page(width=300, height=300)
            with (root / "blank.pdf").open("wb") as handle:
                writer.write(handle)
            (root / "good.txt").write_text("仍可读取", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "没有可提取文本"):
                load_pdf(root / "blank.pdf")
            self.assertEqual([doc["source"] for doc in load_document_tree(root)], ["good.txt"])

    def test_real_pdf_page_metadata_and_corpus_isolation(self):
        corpus = ROOT / "data/cnooc"
        with (corpus / "sources.csv").open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        documents = load_document_tree(corpus)

        self.assertEqual(len(documents), len(rows))
        self.assertEqual({doc["source"] for doc in documents}, {row["file_name"] for row in rows})
        self.assertFalse({"employee_policy.md", "it_policy.md", "travel_policy.md", "security_policy.txt"} & {doc["source"] for doc in documents})
        for document in documents:
            row = next(row for row in rows if row["file_name"] == document["source"])
            self.assertEqual(document["page_count"], int(row["page_count"]))
            self.assertEqual(
                [page["page_number"] for page in document["pages"]],
                list(range(1, document["page_count"] + 1)),
            )
            self.assertTrue(document["text"])
            self.assertEqual(document["page_errors"], [])
            self.assertEqual(Path(document["file_path"]).resolve(), (ROOT / row["relative_path"]).resolve())


if __name__ == "__main__":
    unittest.main()
