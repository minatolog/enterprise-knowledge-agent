
from hybrid_retrieval import retrieve_with_reranker
from llm import answer_with_context
from schemas import RAGResponse


TOP_K = 3
CANDIDATE_K = 5


def main():
    question = input("请输入你的问题：").strip()

    if not question:
        print("问题不能为空。")
        return

    print("\n正在执行 Hybrid Search + Reranker...")

    try:
        # 1. 混合检索 + Cross-Encoder 重排序
        results = retrieve_with_reranker(
            question=question,
            k=TOP_K,
            candidate_k=CANDIDATE_K
        )

        if not results:
            response = RAGResponse(
                answer="根据当前企业知识库无法回答该问题。",
                sources=[],
                rerank_score=None
            )
            print(response.model_dump_json(indent=2))
            return

        # 2. 打印检索结果，方便调试
        print("\n========== Retrieval Results ==========")

        for rank, result in enumerate(results, start=1):
            print(
                f'{rank}. {result["source"]} > '
                f'{result["section"]} | '
                f'Rerank={result["rerank_score"]:.4f}'
            )

        # 3. 整理上下文，并分配引用编号
        contexts = []
        sources = []

        for index, result in enumerate(results, start=1):
            source = (
                f'{result["source"]} > '
                f'{result["section"]}'
            )

            if source not in sources:
                sources.append(source)

            contexts.append(
                f"[资料 {index}]\n"
                f"来源：{source}\n"
                f"内容：{result['text']}"
            )

        context = "\n\n".join(contexts)

        # 4. 调用 DeepSeek
        print("\n正在生成答案...")

        answer = answer_with_context(
            question=question,
            context=context
        )

        if answer.startswith("LLM API 调用失败："):
            raise RuntimeError(answer)

        # 5. Pydantic 结构化结果
        response = RAGResponse(
            answer=answer,
            sources=sources,
            rerank_score=results[0]["rerank_score"]
        )

        print("\n========== 最终结果 ==========")
        print(response.model_dump_json(indent=2))

    except Exception as e:
        print(f"\n程序运行失败：{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
