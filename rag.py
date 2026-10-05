from pathlib import Path


def load_document(file_path: str) -> str:
    path = Path(file_path)

    with open(path, "r", encoding="utf-8") as file:
        return file.read()


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


if __name__ == "__main__":

    file_path = "data/employee_policy.md"

    document = load_document(file_path)

    chunks = split_by_markdown_heading(
        document,
        source="employee_policy.md"
    )

    for chunk in chunks:
        print(chunk)
