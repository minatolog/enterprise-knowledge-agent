from pathlib import Path
import warnings

from pypdf import PdfReader
from docx import Document as DocxDocument


SUPPORTED_EXTENSIONS = {
    ".md",
    ".txt",
    ".pdf",
    ".docx",
}


def load_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_pdf_pages(path: Path) -> tuple[list[dict], list[dict]]:
    """Extract each page independently so one bad page does not hide the rest."""
    reader = PdfReader(path)
    pages = []
    errors = []

    for page_number, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            text = ""
            error = {"page_number": page_number, "error": str(exc)}
            errors.append(error)
            warnings.warn(
                f"PDF 页面读取失败：{path} 第 {page_number} 页：{exc}",
                RuntimeWarning,
                stacklevel=2,
            )
        pages.append({"page_number": page_number, "text": text})

    if not any(page["text"].strip() for page in pages):
        raise ValueError(f"PDF 没有可提取文本：{path}")

    return pages, errors


def load_pdf(path: Path) -> str:
    """Keep the original text-returning interface for existing callers."""
    pages, _ = _extract_pdf_pages(path)
    return "\n".join(page["text"] for page in pages if page["text"])


def load_docx(path: Path) -> str:
    document = DocxDocument(path)

    paragraphs = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if text:
            paragraphs.append(text)

    return "\n".join(paragraphs)


def load_document(path: Path) -> dict:
    path = Path(path)
    extension = path.suffix.lower()
    pdf_pages = None
    page_errors = None

    if extension in {".md", ".txt"}:
        text = load_text_file(path)

    elif extension == ".pdf":
        pdf_pages, page_errors = _extract_pdf_pages(path)
        text = "\n".join(page["text"] for page in pdf_pages if page["text"])

    elif extension == ".docx":
        text = load_docx(path)

    else:
        raise ValueError(
            f"暂不支持文件类型：{extension}"
        )

    document = {
        "source": path.name,
        "file_path": str(path),
        "file_type": extension,
        "text": text
    }

    if pdf_pages is not None:
        document["pages"] = pdf_pages
        document["page_count"] = len(pdf_pages)
        document["page_errors"] = page_errors

    return document


def load_all_documents(
    data_dir: str = "data",
    *,
    recursive: bool = False,
) -> list[dict]:

    documents = []

    directory = Path(data_dir)
    paths = directory.rglob("*") if recursive else directory.iterdir()
    seen_paths = set()

    for path in sorted(paths):

        if not path.is_file():
            continue

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        resolved_path = path.resolve()
        if resolved_path in seen_paths:
            continue
        seen_paths.add(resolved_path)

        try:
            document = load_document(path)
            documents.append(document)

        except Exception as e:
            print(
                f"读取失败：{path.name} | {e}"
            )

    return documents


def load_document_tree(data_dir: str) -> list[dict]:
    """Read one selected corpus recursively without changing the default scope."""
    return load_all_documents(data_dir, recursive=True)


if __name__ == "__main__":

    documents = load_all_documents()

    print(
        f"成功读取 {len(documents)} 份文档"
    )

    for document in documents:

        print("\n====================")

        print(
            "文件：",
            document["source"]
        )

        print(
            "类型：",
            document["file_type"]
        )

        print(
            "字符数：",
            len(document["text"])
        )

        print(
            "内容预览："
        )

        print(
            document["text"][:200]
        )
