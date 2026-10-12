import chromadb

from sentence_transformers import SentenceTransformer

from rag import build_chunks


DB_PATH = "chroma_db"
COLLECTION_NAME = "enterprise_knowledge"


# 1. 加载我们之前一直使用的中文 Embedding 模型
model = SentenceTransformer(
    "BAAI/bge-small-zh-v1.5"
)


# 2. 自动读取 data/ 中的文档并切块
chunks = build_chunks("data")


# 3. 为 Embedding 准备文本
texts = [
    f'{chunk["section"]}\n{chunk["text"]}'
    for chunk in chunks
]


# 4. 提前计算所有企业文档的 Embedding
embeddings = model.encode(
    texts,
    normalize_embeddings=True
).tolist()


# 5. 创建本地持久化 Chroma 数据库
client = chromadb.PersistentClient(
    path=DB_PATH
)


# 6. 创建 / 获取企业知识库 Collection
collection = client.get_or_create_collection(
    name=COLLECTION_NAME
)


# 7. 为每个 Chunk 创建稳定 ID
ids = [
    f'{chunk["source"]}::{chunk["section"]}'
    for chunk in chunks
]


# 8. 保存 Metadata
metadatas = [
    {
        "source": chunk["source"],
        "section": chunk["section"]
    }
    for chunk in chunks
]


# 9. 把文档、Embedding、Metadata 一起存入 Chroma
collection.upsert(
    ids=ids,
    documents=texts,
    embeddings=embeddings,
    metadatas=metadatas
)


print("向量数据库建立完成！")
print(f"共存储 {collection.count()} 个 Chunk")
print(f"数据库位置：{DB_PATH}")