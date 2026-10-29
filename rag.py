from ingestion import load_all_documents
from ingestion import load_document
from pathlib import Path
from knowledge_config import INDEXED_DOCUMENTS, KNOWLEDGE_BASE, ROOT, selected_paths


def split_by_markdown_heading(
    text: str,
    source: str
) -> list[dict]:

    chunks = []

    current_section = None
    current_content = []

    for line in text.splitlines():

        if line.startswith("## "):

            if current_section is not None:

                content = "\n".join(
                    current_content
                ).strip()

                if content:
                    chunks.append(
                        {
                            "text": content,
                            "source": source,
                            "section": current_section
                        }
                    )

            current_section = (
                line.replace("## ", "")
                .strip()
            )

            current_content = []

        else:

            if current_section is not None:
                current_content.append(line)

    if current_section is not None:

        content = "\n".join(
            current_content
        ).strip()

        if content:
            chunks.append(
                {
                    "text": content,
                    "source": source,
                    "section": current_section
                }
            )

    return chunks


def split_plain_text(
    text: str,
    source: str,
    chunk_size: int = 500,
    overlap: int = 80
) -> list[dict]:

    text = text.strip()

    if not text:
        return []

    chunks = []

    start = 0
    chunk_index = 1

    while start < len(text):

        end = min(
            start + chunk_size,
            len(text)
        )

        chunk_text = text[start:end].strip()

        if chunk_text:

            chunks.append(
                {
                    "text": chunk_text,
                    "source": source,
                    "section": f"chunk-{chunk_index}"
                }
            )

            chunk_index += 1

        if end >= len(text):
            break

        start = end - overlap

    return chunks


def chunk_document(
    document: dict
) -> list[dict]:
    file_type = document["file_type"]
    path = document["file_path"]
    try:
        relative_path = str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        relative_path = str(path)

    if file_type == ".pdf":
        chunks = []
        for page in document["pages"]:
            lines = page["text"].splitlines(keepends=True)
            current = []
            size = 0
            pieces = []
            for line in lines:
                if current and size + len(line) > 700:
                    pieces.append("".join(current).strip())
                    current, size = [], 0
                if len(line) > 700:
                    if current:
                        pieces.append("".join(current).strip())
                        current, size = [], 0
                    pieces.extend(part["text"] for part in split_plain_text(
                        line, document["source"], chunk_size=700, overlap=80
                    ))
                else:
                    current.append(line)
                    size += len(line)
            if current:
                pieces.append("".join(current).strip())
            for number, text in enumerate((piece for piece in pieces if piece), start=1):
                chunks.append({
                    "chunk_id": f"{relative_path}::p{page['page_number']:04d}::c{number:04d}",
                    "text": text,
                    "source": document["source"],
                    "relative_path": relative_path,
                    "knowledge_base": KNOWLEDGE_BASE,
                    "page_start": page["page_number"],
                    "page_end": page["page_number"],
                    "section": "",
                })
        return chunks

    if file_type == ".md":

        chunks = split_by_markdown_heading(
            document["text"],
            document["source"]
        )

        # 防止 Markdown 没有 ## 标题
        if chunks:
            return _add_metadata(chunks, document, relative_path)

    chunks = split_plain_text(
        document["text"],
        document["source"]
    )
    return _add_metadata(chunks, document, relative_path)


def _add_metadata(chunks: list[dict], document: dict, relative_path: str) -> list[dict]:
    for number, chunk in enumerate(chunks, start=1):
        chunk.update({
            "chunk_id": f"{relative_path}::c{number:04d}",
            "relative_path": relative_path,
            "knowledge_base": KNOWLEDGE_BASE,
            "page_start": 0,
            "page_end": 0,
        })
    return chunks


def build_chunks(
    data_dir: str | None = None
) -> list[dict]:
    if data_dir is None:
        paths = selected_paths()
        documents = [load_document(paths[name]) for name in INDEXED_DOCUMENTS]
    else:
        documents = load_all_documents(data_dir, recursive=True)

    all_chunks = []

    for document in documents:

        chunks = chunk_document(
            document
        )

        all_chunks.extend(chunks)

    return all_chunks


if __name__ == "__main__":

    chunks = build_chunks()

    print(
        f"共生成 {len(chunks)} 个 Chunk"
    )

    for chunk in chunks:

        print("\n====================")
        print("来源：", chunk["source"])
        print("章节：", chunk["section"])
        print("内容：")
        print(chunk["text"])
