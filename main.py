from retrieval import retrieve_top_k
from llm import answer_with_context
from schemas import RAGResponse


question = input("请输入你的问题：").strip()


# 1. 从 Chroma 检索最相关的资料
results = retrieve_top_k(
    question,
    k=3
)


# 2. 把检索结果整理成 LLM Context
contexts = []

for result in results:
    contexts.append(
        f"""
来源：{result["source"]}
章节：{result["section"]}

{result["text"]}
"""
    )

context = "\n\n".join(contexts)


# 3. 让 DeepSeek 根据检索资料回答
answer = answer_with_context(
    question=question,
    context=context
)


# 4. 来源由程序生成，不让 LLM 自己编
sources = []

for result in results:
    source = f'{result["source"]} > {result["section"]}'

    if source not in sources:
        sources.append(source)


# 5. Top-1 的向量距离
retrieval_distance = results[0]["distance"]


# 6. Pydantic 生成最终结构化结果
response = RAGResponse(
    answer=answer,
    sources=sources,
    retrieval_distance=retrieval_distance
)


# 7. 输出 JSON
print("\n最终结果：")
print(
    response.model_dump_json(
        indent=2
    )
)