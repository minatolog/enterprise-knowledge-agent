from pathlib import Path


def load_document(file_path: str) -> str:
    path = Path(file_path)

    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def load_all_documents(data_dir: str = "data") -> list[dict]:
    # data_dir 默认是 data 文件夹；返回的列表中，每个字典代表一份文档。
    documents = []

    # glob("*.md") 找到该文件夹当前这一层的所有 Markdown 文件。
    for path in Path(data_dir).glob("*.md"):
        # 按 UTF-8 读取文件全文，避免中文出现乱码。
        text = path.read_text(encoding="utf-8")

        # 同时保存文件名和正文，后续检索时才能标明资料来源。
        documents.append(
            {
                "source": path.name,
                "text": text
            }
        )

    # 把找到的所有文档交给调用者。
    return documents

def split_by_markdown_heading(
    text: str,
    source: str
) -> list[dict]:
    # 每个 Chunk 是一个字典：正文 text、文件来源 source、章节 section。
    chunks = []

    current_section = None
    current_content = []

    for line in text.splitlines():

        if line.startswith("## "):

            # 保存前一个 section
            if current_section is not None:
                chunks.append(
                    {
                        "text": "\n".join(current_content).strip(),
                        "source": source,
                        "section": current_section
                    }
                )

            # 去掉 Markdown 标题标记，记录章节名，并开始收集新章节正文。
            current_section = line.replace("## ", "").strip()
            current_content = []

        else:
            if current_section is not None:
                current_content.append(line)

    # 保存最后一个 section
    if current_section is not None:
        chunks.append(
            {
                "text": "\n".join(current_content).strip(),
                "source": source,
                "section": current_section
            }
        )

    return chunks

def build_chunks(data_dir: str = "data") -> list[dict]:
    # 先读取文件夹中的全部 Markdown 文档。
    documents = load_all_documents(data_dir)

    # 汇总每份文档切出来的 Chunk。
    all_chunks = []

    for document in documents:
        # 按二级标题切分正文，并把原文件名传给每个 Chunk。
        chunks = split_by_markdown_heading(
            document["text"],
            source=document["source"]
        )

        # extend 会把本篇文档的所有 Chunk 逐项加入总列表。
        all_chunks.extend(chunks)

    # 返回来自所有文档的 Chunk；每项包含正文、来源和章节。
    return all_chunks

if __name__ == "__main__":

    file_path = "data/employee_policy.md"

    document = load_document(file_path)

    chunks = split_by_markdown_heading(
        document,
        source="employee_policy.md"
    )

    for chunk in chunks:
        print(chunk)
