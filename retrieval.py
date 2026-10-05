from sentence_transformers import SentenceTransformer, util

from rag import load_document, split_by_markdown_heading


# 1. 加载中文 Embedding 模型
model = SentenceTransformer("BAAI/bge-small-zh-v1.5")


# 2. 读取企业文档
document = load_document("data/employee_policy.md")


# 3. 把文档切成多个 Chunk
chunks = split_by_markdown_heading(document)


# 4. 把每个 Chunk 转换成向量
chunk_embeddings = model.encode(
    chunks,
    convert_to_tensor=True
)


def retrieve_top_k(question: str, k: int = 3):
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

    for score, index in zip(
        top_results.values,
        top_results.indices
    ):
        results.append(
            {
                "chunk": chunks[index.item()],
                "score": score.item()
            }
        )

    return results#改成topk搜索了

if __name__ == "__main__":
    question = "年假应该怎么申请，没用完怎么办？"

    results = retrieve_top_k(question, k=3)

    print("用户问题：")
    print(question)

    for i, result in enumerate(results, start=1):
        print(f"\n--- Top {i} ---")
        print(f"相似度：{result['score']:.4f}")
        print(result["chunk"])