from pathlib import Path


def load_document(file_path: str) -> str:
    path = Path(file_path)

    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def split_by_markdown_heading(text: str) -> list[str]:
    chunks = []
    current_chunk = []

    for line in text.splitlines():
        # 遇到新的二级标题时，先保存前一个 Chunk
        if line.startswith("## "):
            if current_chunk:
                chunk = "\n".join(current_chunk).strip()

                if chunk:
                    chunks.append(chunk)

            # 新标题作为新 Chunk 的开头
            current_chunk = [line]

        else:
            # 只有已经进入某个二级标题后，才继续加入内容
            if current_chunk:
                current_chunk.append(line)

    # 最后一个 Chunk 不会再遇到下一个标题，所以手动保存
    if current_chunk:
        chunk = "\n".join(current_chunk).strip()

        if chunk:
            chunks.append(chunk)

    return chunks


if __name__ == "__main__":
    document = load_document("data/employee_policy.md")

    chunks = split_by_markdown_heading(document)

    print(f"总共切成 {len(chunks)} 个 Chunk")

    for index, chunk in enumerate(chunks):
        print(f"\n--- Chunk {index + 1} ---")
        print(chunk)