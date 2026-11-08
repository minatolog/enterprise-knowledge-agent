
"""CLI entry point using the same RAGService as the API."""

from app.logging_config import configure_logging
from app.service import RAGResult, RAGService, source_label
from schemas import RAGResponse


def _format_score(item: dict) -> str:
    score = item.get("rerank_score")
    if score is None:
        return "n/a"
    try:
        return f"{float(score):.4f}"
    except (TypeError, ValueError):
        return "n/a"


def run_cli(
    service: RAGService | None = None,
    input_func=input,
    output_func=print,
) -> RAGResponse | None:
    configure_logging()
    service = service or RAGService()
    question = input_func("请输入你的问题：").strip()

    if not question:
        output_func("问题不能为空。")
        return None

    output_func("\n正在执行 Hybrid Search + Reranker...")

    def print_retrieval(results: list[dict]) -> None:
        output_func("\n========== Retrieval Results ==========")
        for rank, item in enumerate(results, start=1):
            output_func(
                f"{rank}. {source_label(item)} | "
                f"Rerank={_format_score(item)}"
            )
        output_func("\n正在生成答案...")

    try:
        result: RAGResult = service.answer(question, on_retrieval=print_retrieval)
        response = RAGResponse(
            answer=result.answer,
            sources=result.legacy_sources,
            rerank_score=result.rerank_score,
        )
        output_func("\n========== 最终结果 ==========")
        output_func(response.model_dump_json(indent=2))
        return response
    except Exception as exc:
        output_func(f"\n程序运行失败：{type(exc).__name__}: {exc}")
        return None


def main() -> None:
    run_cli()


if __name__ == "__main__":
    main()
