# Path 是 Python 自带的路径处理工具，用来表示文件或文件夹的位置。
from pathlib import Path


# 定义一个读取文档的函数。
# file_path: str 表示传入的文件路径应该是字符串。
# -> str 表示这个函数会返回字符串，也就是文档中的全部文字。
def load_document(file_path: str) -> str:
    # 把普通的路径字符串转换成 Path 对象，方便进行文件操作。
    path = Path(file_path)

    # 以只读模式（r）打开文件，并使用 UTF-8 编码正确读取中文。
    # with 会在读取结束后自动关闭文件。
    with open(path, "r", encoding="utf-8") as file:
        # file.read() 读取文件的全部内容，return 把内容返回给调用者。
        return file.read()


# 定义一个切分文本的函数。
# 它接收一整段字符串，返回一个字符串列表；列表中的每项都是一个 Chunk。
def split_text(text: str) -> list[str]:
    # \n 代表换行，\n\n 代表一个空行。
    # split() 按照空行切分文本，得到多个段落。
    sections = text.split("\n\n")

    # 创建一个空列表，用来保存清理后的文本块。
    chunks = []

    # 依次取出 sections 中的每个段落。
    for section in sections:
        # strip() 删除段落开头和结尾多余的空格与换行。
        section = section.strip()

        # 只有段落不是空字符串时，才把它添加到 chunks 列表中。
        if section:
            chunks.append(section)

    # 返回最终的文本块列表。
    return chunks


# 只有直接运行 rag.py 时，才执行下面的测试代码。
# 如果其他文件只是导入 load_document 或 split_text，这部分不会自动运行。
if __name__ == "__main__":
    # 读取员工制度文档，并把全部文字保存到 document 变量中。
    document = load_document("data/employee_policy.md")

    # 调用 split_text()，把整篇文档切分成多个 Chunk。
    chunks = split_text(document)

    # len(chunks) 获取文本块的数量；f 字符串可以把结果放进文字中。
    print(f"总共切成 {len(chunks)} 个 Chunk")

    # enumerate() 同时提供文本块的编号 index 和内容 chunk。
    # index 默认从 0 开始，所以显示时使用 index + 1，让编号从 1 开始。
    for index, chunk in enumerate(chunks):
        print(f"\n--- Chunk {index + 1} ---")
        print(chunk)
