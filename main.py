from retrieval import retrieve_top_k
from llm import answer_with_context
from schemas import RAGResponse


# 检索距离阈值
# distance 越小代表越相关
MAX_DISTANCE = 0.9

# 每次最多检索几个 Chunk
TOP_K = 3


def main():

    # 1. 获取用户问题
    question = input("请输入你的问题：").strip()

    if not question:
        print("问题不能为空。")
        return


    # 2. 从 Chroma 向量数据库检索 Top-K
    results = retrieve_top_k(
        question,
        k=TOP_K
    )


    # 3. 如果没有检索结果，直接拒答
    if not results:
        response = RAGResponse(
            answer="根据当前企业知识库无法回答该问题。",
            sources=[],
            retrieval_distance=999.0
        )

        print("\n最终结果：")
        print(response.model_dump_json(indent=2))

        return


    # 4. 检查最相关 Chunk 是否足够相关
    if results[0]["distance"] > MAX_DISTANCE:

        response = RAGResponse(
            answer="根据当前企业知识库无法回答该问题。",
            sources=[],
            retrieval_distance=results[0]["distance"]
        )

        print("\n最终结果：")
        print(response.model_dump_json(indent=2))

        return


    # 5. 过滤掉 Top-K 中不相关的 Chunk
    relevant_results = [
        result
        for result in results
        if result["distance"] <= MAX_DISTANCE
    ]


    # 6. 构造提供给 LLM 的 Context
    contexts = []

    for result in relevant_results:
        contexts.append(
            f"""
来源：{result["source"]}
章节：{result["section"]}

{result["text"]}
"""
        )

    context = "\n\n".join(contexts)


    # 7. 调用 DeepSeek
    answer = answer_with_context(
        question=question,
        context=context
    )


    # 8. 整理来源
    sources = []

    for result in relevant_results:

        source = (
            f'{result["source"]} > '
            f'{result["section"]}'
        )

        # 防止重复来源
        if source not in sources:
            sources.append(source)


    # 9. 使用最相关结果的 distance
    retrieval_distance = relevant_results[0]["distance"]


    # 10. 使用 Pydantic 生成结构化结果
    response = RAGResponse(
        answer=answer,
        sources=sources,
        retrieval_distance=retrieval_distance
    )


    # 11. 输出最终 JSON
    print("\n最终结果：")

    print(
        response.model_dump_json(
            indent=2
        )
    )


if __name__ == "__main__":
    main()