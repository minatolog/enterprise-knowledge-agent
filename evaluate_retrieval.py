
import json
from pathlib import Path

from retrieval import retrieve_top_k


EVAL_FILE = Path("eval/retrieval_cases.json")
MAX_DISTANCE = 0.9


def evaluate():

    with open(EVAL_FILE, "r", encoding="utf-8") as f:
        cases = json.load(f)

    positive_total = 0
    hit_at_1 = 0
    hit_at_3 = 0
    reciprocal_rank_sum = 0.0

    negative_total = 0
    negative_correct = 0

    for case in cases:

        question = case["question"]
        expected_source = case["expected_source"]
        expected_section = case["expected_section"]

        results = retrieve_top_k(question, k=3)

        # 与当前 main.py 一样，使用距离阈值过滤
        relevant_results = [
            result for result in results
            if result["distance"] <= MAX_DISTANCE
        ]

        print(f"\n问题：{question}")

        if expected_source is None:
            negative_total += 1

            rejected = len(relevant_results) == 0
            negative_correct += int(rejected)

            print("预期：拒答")
            print("实际：", "拒答" if rejected else "放行")
            continue

        positive_total += 1
        matched_rank = None

        for rank, result in enumerate(relevant_results, start=1):

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

        print("预期来源：", expected_source, ">", expected_section)
        print("命中排名：", matched_rank or "未命中")

        for index, result in enumerate(results, start=1):
            print(
                f"Top {index}: "
                f'{result["source"]} > {result["section"]} '
                f'distance={result["distance"]:.4f}'
            )

    print("\n========== Evaluation Result ==========")

    if positive_total:
        print(f"Hit@1: {hit_at_1 / positive_total:.2%}")
        print(f"Hit@3: {hit_at_3 / positive_total:.2%}")
        print(f"MRR@3: {reciprocal_rank_sum / positive_total:.4f}")

    if negative_total:
        print(
            "Negative Rejection Accuracy: "
            f"{negative_correct / negative_total:.2%}"
        )


if __name__ == "__main__":
    evaluate()
