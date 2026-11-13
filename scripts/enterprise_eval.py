"""Evaluate prepared answer records; optional real LLM entailment, never fabricate labels."""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def evaluate(records, judge=None):
    results = []
    for row in records:
        evidence = row["evidence"]
        answer = row["answer"]
        numbers = [int(number) for number in re.findall(r"\[资料\s*(\d+)\]", answer)]
        valid = bool(numbers) and all(1 <= number <= len(evidence) for number in numbers)
        human = row.get("human_correct")
        if human is not None and not isinstance(human, bool):
            raise ValueError("human_correct must be a reviewed boolean or null")
        results.append({"id": row["id"], "citation_structure_valid": valid,
            "judge_supported": bool(judge(row["question"], answer, evidence)) if judge else None,
            "human_correct": human, "requires_abstention": row.get("requires_abstention", False)})
    reviewed = [row for row in results if row["human_correct"] is not None]
    return {"count": len(results), "human_reviewed_count": len(reviewed),
        "human_accuracy": sum(row["human_correct"] for row in reviewed) / len(reviewed) if reviewed else None,
        "results": results}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="JSON list containing question, answer and actual retrieved evidence")
    parser.add_argument("--llm-judge", action="store_true", help="Explicitly call the configured model once per record")
    parser.add_argument("--max-calls", type=int, default=3)
    parser.add_argument("--output", type=Path, default=Path(".enterprise/generation-eval.json"))
    args = parser.parse_args()
    records = json.loads(args.input.read_text())
    if not records:
        parser.error("input cannot be empty")
    if args.llm_judge and not 0 < len(records) <= args.max_calls:
        parser.error("record count exceeds explicitly bounded model calls")
    judge = None
    if args.llm_judge:
        from app.enterprise.verification import EvidenceJudge
        judge = EvidenceJudge()
    output = evaluate(records, judge)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print("Evaluated", len(records), "records; human labels and model verdicts remain distinct")


if __name__ == "__main__":
    main()
