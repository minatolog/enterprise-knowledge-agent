from pathlib import Path

import chromadb

from sentence_transformers import (
    SentenceTransformer
)

from document_tracker import (
    detect_changes,
    save_state
)

from ingestion import load_document
from rag import chunk_document


DATA_DIR = Path("data")

DB_PATH = "chroma_db"

COLLECTION_NAME = (
    "enterprise_knowledge"
)


model = SentenceTransformer(
    "BAAI/bge-small-zh-v1.5"
)


client = chromadb.PersistentClient(
    path=DB_PATH
)


collection = (
    client.get_or_create_collection(
        name=COLLECTION_NAME
    )
)


def delete_document_from_index(
    filename: str
):

    collection.delete(
        where={
            "source": filename
        }
    )


def index_document(
    filename: str
):

    path = DATA_DIR / filename

    document = load_document(path)

    chunks = chunk_document(
        document
    )

    if not chunks:

        print(
            f"没有生成 Chunk，跳过："
            f"{filename}"
        )

        return

    texts = [
        (
            f'{chunk["section"]}\n'
            f'{chunk["text"]}'
        )
        for chunk in chunks
    ]

    embeddings = model.encode(
        texts,
        normalize_embeddings=True
    ).tolist()

    ids = [
        (
            f'{filename}::'
            f'{chunk["section"]}'
        )
        for chunk in chunks
    ]

    metadatas = [
        {
            "source": filename,
            "section": chunk["section"]
        }
        for chunk in chunks
    ]

    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas
    )

    print(
        f"已索引：{filename} "
        f"({len(chunks)} chunks)"
    )


def main():

    changes = detect_changes()

    print(
        "新增：",
        changes["added"]
    )

    print(
        "修改：",
        changes["modified"]
    )

    print(
        "删除：",
        changes["deleted"]
    )

    print(
        "未变化：",
        changes["unchanged"]
    )

    try:

        # 已删除文件
        for filename in changes["deleted"]:

            delete_document_from_index(
                filename
            )

            print(
                f"已删除索引：{filename}"
            )

        # 修改文件
        for filename in changes["modified"]:

            delete_document_from_index(
                filename
            )

            index_document(
                filename
            )

        # 新增文件
        for filename in changes["added"]:

            index_document(
                filename
            )

        # 所有 Chroma 操作成功以后
        # 才更新 SHA-256 状态
        save_state(
            changes["current_state"]
        )

        print(
            "\n增量索引更新完成。"
        )

        print(
            f"当前 Chroma 共 "
            f"{collection.count()} 个 Chunk"
        )

    except Exception as e:

        print(
            "\n索引更新失败。"
        )

        print(
            "不会保存新的文件状态。"
        )

        print(e)


if __name__ == "__main__":
    main()