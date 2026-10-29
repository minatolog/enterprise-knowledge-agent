"""Small evidence-backed integration check; not a formal retrieval benchmark."""

import json
import re
from pathlib import Path

from hybrid_retrieval import retrieve_hybrid, retrieve_with_reranker
from retrieval import retrieve_top_k

ROOT = Path(__file__).resolve().parent
CASES = ROOT / "eval" / "cnooc_smoke_cases.json"
OUTPUT = ROOT / "reports" / "cnooc_migration_smoke.json"


def compact(text):
    return re.sub(r"\s+", "", text)


def main():
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    records = []
    methods = {
        "vector": retrieve_top_k,
        "hybrid": retrieve_hybrid,
        "reranked": retrieve_with_reranker,
    }
    for case in cases:
        record = {"question": case["question"], "expected_source": case["expected_source"],
                  "expected_page": case["expected_page"], "methods": {}}
        for method, retrieve in methods.items():
            results = retrieve(case["question"], k=3)
            candidates = []
            for item in results:
                candidates.append({
                    "chunk_id": item["chunk_id"],
                    "source": item["relative_path"],
                    "page": item["page_start"],
                    "rerank_score": item.get("rerank_score"),
                    "evidence_match": (
                        item["relative_path"] == case["expected_source"]
                        and item["page_start"] <= case["expected_page"] <= item["page_end"]
                        and compact(case["evidence"]) in compact(item["text"])
                    ),
                })
            record["methods"][method] = candidates
        records.append(record)
        top = record["methods"]["reranked"][0]
        print(f'{case["question"]} -> {top["source"]} p.{top["page"]} '
              f'score={top["rerank_score"]:.4f} evidence={top["evidence_match"]}', flush=True)
    OUTPUT.write_text(json.dumps({"label": "smoke test only, not a formal accuracy estimate",
                                  "cases": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"记录已保存：{OUTPUT}")


if __name__ == "__main__":
    main()
