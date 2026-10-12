import chromadb

from sentence_transformers import SentenceTransformer


DB_PATH = "chroma_db"
COLLECTION_NAME = "enterprise_knowledge"

# 查询时仍然要用同一个 Embedding 模型
model = SentenceTransformer(
    "BAAI/bge-small-zh-v1.5"
)

# 直接打开已经存在的向量数据库
client = chromadb.PersistentClient(
    path=DB_PATH
)

collection = client.get_collection(
    name=COLLECTION_NAME
)


def retrieve_top_k(question: str, k: int = 3) -> list[dict]:

    # 只对“用户问题”做 Embedding
    question_embedding = model.encode(
        question,
        normalize_embeddings=True
    ).tolist()

    # 直接从 Chroma 搜索
    result = collection.query(
        query_embeddings=[question_embedding],
        n_results=k,
        include=[
            "documents",
            "metadatas",
            "distances"
        ]
    )

    results = []

    for document, metadata, distance in zip(
        result["documents"][0],
        result["metadatas"][0],
        result["distances"][0]
    ):
        results.append(
            {
                "text": document,
                "source": metadata["source"],
                "section": metadata["section"],
                "distance": distance
            }
        )

    return results


if __name__ == "__main__":

    question = "国内出差酒店最多可以报多少钱？"

    results = retrieve_top_k(
        question,
        k=3
    )

    print("用户问题：")
    print(question)

    for index, result in enumerate(
        results,
        start=1
    ):
        print(f"\n--- Top {index} ---")
        print("来源：", result["source"])
        print("章节：", result["section"])
        print("距离：", result["distance"])
        print("内容：")
        print(result["text"])

    test_questions = [
        "员工一年有多少天年假？",
        "国内出差酒店最多报销多少钱？",
        "公司电脑可以随便安装软件吗？",
        "公司老板今天午饭吃了什么？",
        "今年公司股票会涨多少？"
    ]

    for question in test_questions:
        results = retrieve_top_k(question, k=1)

        print("\n问题：", question)
        print("Top 1：", results[0]["source"], ">", results[0]["section"])
        print("Distance：", results[0]["distance"])
