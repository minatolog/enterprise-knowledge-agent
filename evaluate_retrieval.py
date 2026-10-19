
"""对比 Vector-only、Hybrid 和 Hybrid + Reranker 检索效果。"""

import json
from pathlib import Path

from retrieval import retrieve_top_k
from hybrid_retrieval import retrieve_hybrid, retrieve_with_reranker


EVAL_FILE = Path(__file__).resolve().parent / "eval" / "retrieval_cases.json"
TOP_K = 3


def evaluate_retriever(name, retrieve_fn, cases):
    total = 0
    hit_at_1 = 0
    hit_at_3 = 0
    reciprocal_rank_sum = 0.0

    print(f"\n========== {name} ==========")

    for case in cases:
        expected_source = case["expected_source"]
        expected_section = case["expected_section"]

        # 无答案问题单独评测拒答，不纳入排序指标
        if expected_source is None:
            continue

        total += 1
        question = case["question"]

        results = retrieve_fn(question, k=TOP_K)

        matched_rank = None

        for rank, result in enumerate(results, start=1):
            if (
                result["source"] == expected_source
                and result["section"] == expected_section
            ):
                matched_rank = rank
                break

        if matched_rank is not None:
            hit_at_3 += 1
            reciprocal_rank_sum += 1 / matched_rank

            if matched_rank == 1:
                hit_at_1 += 1

        print(
            f"{question} -> Rank: "
            f"{matched_rank if matched_rank is not None else '未命中'}"
        )

    if total == 0:
        raise ValueError("评测集中没有有标准来源的问题。")

    return {
        "Hit@1": hit_at_1 / total,
        "Hit@3": hit_at_3 / total,
        "MRR@3": reciprocal_rank_sum / total,
    }


def main():
    if not EVAL_FILE.is_file():
        raise FileNotFoundError(f"找不到评测数据集：{EVAL_FILE}")

    cases = json.loads(
        EVAL_FILE.read_text(encoding="utf-8")
    )

    vector_metrics = evaluate_retriever(
        "Vector-only",
        retrieve_top_k,
        cases
    )

    hybrid_metrics = evaluate_retriever(
        "Hybrid Search",
        retrieve_hybrid,
        cases
    )

    reranker_metrics = evaluate_retriever(
        "Hybrid + Reranker",
        retrieve_with_reranker,
        cases
    )

    print("\n========== Comparison ==========")

    print(
        f'{"Metric":<12} '
        f'{"Vector":>12} '
        f'{"Hybrid":>12} '
        f'{"Reranker":>12}'
    )

    for metric in ("Hit@1", "Hit@3", "MRR@3"):
        print(
            f"{metric:<12} "
            f"{vector_metrics[metric]:>12.2%} "
            f"{hybrid_metrics[metric]:>12.2%} "
            f"{reranker_metrics[metric]:>12.2%}"
        )

    answerable = sum(
        case["expected_source"] is not None
        for case in cases
    )

    print(f"\n有答案评测问题：{answerable} 道")
    print("注：未应用距离阈值，不评估无答案拒答及 LLM 生成质量。")


if __name__ == "__main__":
    main()
