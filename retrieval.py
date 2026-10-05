from sentence_transformers import SentenceTransformer, util

from rag import load_document, split_by_markdown_heading


# 1. 加载中文 Embedding 模型
model = SentenceTransformer("BAAI/bge-small-zh-v1.5")


# 2. 读取企业文档
document = load_document("data/employee_policy.md")


# 3. 把文档切成多个 Chunk
chunks = split_by_markdown_heading(
    document,
    source="employee_policy.md"
)


# Chunk 是包含正文和来源的字典；Embedding 模型只需要正文字符串。
chunk_texts = [
    chunk["text"]
    for chunk in chunks
]

chunk_embeddings = model.encode(
    chunk_texts,
    convert_to_tensor=True
)


def retrieve_top_k(question: str, k: int = 3):
    # 问题和文档都用同一个模型转换为向量，才能比较相似度。
    question_embedding = model.encode(
        question,
        convert_to_tensor=True
    )

    scores = util.cos_sim(
        question_embedding,
        chunk_embeddings
    )[0]

    # 防止 k 大于实际 Chunk 数量
    k = min(k, len(chunks))

    top_results = scores.topk(k)

    results = []

    # 每个分数都对应一个 Chunk；保留正文、来源、章节及分数。
    for score, index in zip(
        top_results.values,
        top_results.indices
    ):
        chunk = chunks[index.item()]
        results.append(
            {
                "text": chunk["text"],
                "source": chunk["source"],
                "section": chunk["section"],
                "score": score.item()
            }
        )

    return results

if __name__ == "__main__":

    question = "员工一年有多少天年假？"

    results = retrieve_top_k(
        question,
        k=3
    )

    for i, result in enumerate(results, start=1):

        print(f"\n--- Top {i} ---")

        print("来源：", result["source"])
        print("章节：", result["section"])
        print("相似度：", result["score"])
        print("内容：")
        print(result["text"])
