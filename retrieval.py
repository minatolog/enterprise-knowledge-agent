from sentence_transformers import SentenceTransformer, util

from rag import load_document, split_by_markdown_heading


# 1. 加载中文 Embedding 模型
model = SentenceTransformer("BAAI/bge-small-zh-v1.5")

document = load_document("data/employee_policy.md")


# 3. 把文档切成多个 Chunk
chunks = split_by_markdown_heading(document)


# 4. 把每个 Chunk 转换成向量
chunk_embeddings = model.encode(
    chunks,
    convert_to_tensor=True
)


def retrieve_best_chunk(question: str) -> tuple[str, float]:
    question_embedding = model.encode(
        question,
        convert_to_tensor=True
    )

    scores = util.cos_sim(
        question_embedding,
        chunk_embeddings
    )[0]

    best_index = scores.argmax().item()

    return chunks[best_index], scores[best_index].item()


if __name__ == "__main__":
    question = "员工一年有多少天年假？"

    chunk, score = retrieve_best_chunk(question)

    print("最相关的 Chunk：")
    print(chunk)

    print("\n相似度：")
    print(score)