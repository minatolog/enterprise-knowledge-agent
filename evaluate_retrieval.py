
import json
from pathlib import Path

from retrieval import retrieve_top_k
from hybrid_retrieval import retrieve_hybrid


EVAL_FILE = Path("eval/retrieval_cases.json")


def evaluate_retriever(name, retrieve_fn, cases):
    total = 0
    hit1 = 0
    hit3 = 0
    reciprocal_rank_sum = 0.0

    print(f"\n===== {name} =====")

    for case in cases:
        expected_source = case["expected_source"]
        expected_section = case["expected_section"]

        # 无答案问题暂不纳入排序指标
        if expected_source is None:
            continue

        total += 1
        question = case["question"]

        results = retrieve_fn(question, k=3)
        matched_rank = None

        for rank, result in enumerate(results, 1):
            if (
                result["source"] == expected_source
                and result["section"] == expected_section
            ):
                matched_rank = rank
                break

        if matched_rank is not None:
            hit3 += 1
            reciprocal_rank_sum += 1 / matched_rank

            if matched_rank == 1:
                hit1 += 1

        print(
            f"{question} → "
            f"Rank: {matched_rank or '未命中'}"
        )

    metrics = {
        "Hit@1": hit1 / total if total else 0,
        "Hit@3": hit3 / total if total else 0,
        "MRR@3": reciprocal_rank_sum / total if total else 0
    }

    return metrics


def main():
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

    print("\n===== Comparison =====")
    print(f'{"Metric":<12} {"Vector":>12} {"Hybrid":>12}')

    for metric in vector_metrics:
        print(
            f"{metric:<12} "
            f"{vector_metrics[metric]:>12.2%} "
            f"{hybrid_metrics[metric]:>12.2%}"
        )


if __name__ == "__main__":
    main()
