import tempfile
from pathlib import Path

from ingestion import load_document


def parse_bytes(data: bytes, suffix: str, mode: str = "basic"):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / f"document{suffix}"
        path.write_bytes(data)
        if mode == "docling" and suffix == ".pdf":
            from docling.document_converter import DocumentConverter
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.document_converter import PdfFormatOption
            from docling.datamodel.base_models import InputFormat
            options = PdfPipelineOptions(do_ocr=True, do_table_structure=True)
            converter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})
            converted = converter.convert(path, raises_on_error=True).document
            pages = {}
            for item, _level in converted.iterate_items():
                text = item.export_to_markdown(doc=converted) if hasattr(item, "export_to_markdown") else getattr(item, "text", "")
                provenance = getattr(item, "prov", [])
                for page in {prov.page_no for prov in provenance}:
                    if text:
                        pages.setdefault(page, []).append(text)
            if not pages:
                raise ValueError("document conversion produced no page-level content")
            return [{"page_number": page, "text": "\n".join(texts)} for page, texts in sorted(pages.items())]
        document = load_document(path)
        if document.get("page_errors"):
            raise ValueError("document contains failed pages; use OCR parser or repair the source")
        return document.get("pages") or [{"page_number": 1, "text": document["text"]}]
