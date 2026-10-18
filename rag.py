from ingestion import load_all_documents


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

    if file_type == ".md":

        chunks = split_by_markdown_heading(
            document["text"],
            document["source"]
        )

        # 防止 Markdown 没有 ## 标题
        if chunks:
            return chunks

    return split_plain_text(
        document["text"],
        document["source"]
    )


def build_chunks(
    data_dir: str = "data"
) -> list[dict]:

    documents = load_all_documents(
        data_dir
    )

    all_chunks = []

    for document in documents:

        chunks = chunk_document(
            document
        )

        all_chunks.extend(chunks)

    return all_chunks


if __name__ == "__main__":

    chunks = build_chunks("data")

    print(
        f"共生成 {len(chunks)} 个 Chunk"
    )

    for chunk in chunks:

        print("\n====================")
        print("来源：", chunk["source"])
        print("章节：", chunk["section"])
        print("内容：")
        print(chunk["text"])