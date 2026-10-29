
import json
import argparse
from pathlib import Path

from hybrid_retrieval import retrieve_with_reranker


def main():
    parser = argparse.ArgumentParser(description="阈值校准仅限显式指定的数据集；旧模拟题已归档。")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = json.loads(
        args.dataset.read_text(encoding="utf-8")
    )

    records = []

    print("\n===== Reranker Score Calibration =====")

    for case in cases:
        question = case["question"]

        results = retrieve_with_reranker(
            question=question,
            k=3,
            candidate_k=5
        )

        top_score = (
            float(results[0]["rerank_score"])
            if results else 0.0
        )

        top_source = (
            results[0]["source"]
            if results else "None"
        )

        record = {
            "question": question,
            "answerable": case["answerable"],
            "score": top_score,
            "top_source": top_source
        }

        records.append(record)

        label = (
            "有答案" if case["answerable"]
            else "无答案"
        )

        print(
            f"{label} | "
            f"score={top_score:.6f} | "
            f"{question} | {top_source}"
        )

    print("\n===== Threshold Comparison =====")

    # 初步候选阈值：不是最终推荐阈值
    thresholds = [
        0.01, 0.05, 0.10, 0.20,
        0.30, 0.40, 0.50, 0.60,
        0.70, 0.80, 0.90
    ]

    for threshold in thresholds:
        tp = fp = tn = fn = 0

        for record in records:
            predicted_answerable = (
                record["score"] >= threshold
            )
            actual = record["answerable"]

            if predicted_answerable and actual:
                tp += 1
            elif predicted_answerable and not actual:
                fp += 1
            elif not predicted_answerable and not actual:
                tn += 1
            else:
                fn += 1

        recall = tp / (tp + fn) if tp + fn else 0
        rejection = tn / (tn + fp) if tn + fp else 0

        print(
            f"Threshold={threshold:.2f} | "
            f"Answer Recall={recall:.2%} | "
            f"Negative Rejection={rejection:.2%} | "
            f"FP={fp} FN={fn}"
        )

    output = args.output
    output.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"\n实验结果已保存：{output}")


if __name__ == "__main__":
    main()
