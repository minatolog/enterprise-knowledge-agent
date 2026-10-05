from retrieval import retrieve_top_k
from llm import answer_with_context
from schemas import RAGResponse


question = "一年又多少年假？"

results = retrieve_top_k(
    question,
    k=3
)


# 拼接给 LLM 的上下文
contexts = []

for result in results:
    contexts.append(
        f"""
来源：{result["source"]}
章节：{result["section"]}

{result["text"]}
"""
    )

context = "\n".join(contexts)


# 调用 LLM
answer = answer_with_context(
    question=question,
    context=context
)


# 来源由程序生成，而不是让 LLM 猜
sources = [
    f'{result["source"]} > {result["section"]}'
    for result in results
]


# 最高检索相似度
retrieval_score = results[0]["score"]


# Pydantic 结构化结果
rag_response = RAGResponse(
    answer=answer,
    sources=sources,
    retrieval_score=retrieval_score
)


print(rag_response.model_dump_json(indent=2))