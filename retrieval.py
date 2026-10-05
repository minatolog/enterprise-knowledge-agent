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


# 5. 用户问题
question = "员工一年有多少天年假？"


# 6. 把问题也转换成向量
question_embedding = model.encode(
    question,
    convert_to_tensor=True
)


# 7. 计算问题和所有 Chunk 的余弦相似度
scores = util.cos_sim(
    question_embedding,
    chunk_embeddings
)[0]


# 8. 找到相似度最高的 Chunk
best_index = scores.argmax().item()


print("用户问题：")
print(question)

print("\n最相关的 Chunk：")
print(chunks[best_index])

print("\n相似度：")
print(scores[best_index].item())