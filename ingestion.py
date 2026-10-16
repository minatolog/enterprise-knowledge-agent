from pathlib import Path

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


def load_pdf(path: Path) -> str:
    reader = PdfReader(path)

    pages = []

    for page in reader.pages:
        text = page.extract_text()

        if text:
            pages.append(text)

    return "\n".join(pages)


def load_docx(path: Path) -> str:
    document = DocxDocument(path)

    paragraphs = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if text:
            paragraphs.append(text)

    return "\n".join(paragraphs)


def load_document(path: Path) -> dict:
    extension = path.suffix.lower()

    if extension in {".md", ".txt"}:
        text = load_text_file(path)

    elif extension == ".pdf":
        text = load_pdf(path)

    elif extension == ".docx":
        text = load_docx(path)

    else:
        raise ValueError(
            f"暂不支持文件类型：{extension}"
        )

    return {
        "source": path.name,
        "file_path": str(path),
        "file_type": extension,
        "text": text
    }


def load_all_documents(
    data_dir: str = "data"
) -> list[dict]:

    documents = []

    for path in Path(data_dir).iterdir():

        if not path.is_file():
            continue

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        try:
            document = load_document(path)
            documents.append(document)

        except Exception as e:
            print(
                f"读取失败：{path.name} | {e}"
            )

    return documents


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