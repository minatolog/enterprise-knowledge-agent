"""Reproducible CNOOC retrieval comparison.

This script compares four retrieval configurations on the same dataset and the
same copied Chroma snapshot:

1. Dense-only (BGE embedding + Chroma)
2. BM25-only (jieba + BM25Okapi)
3. Hybrid (Dense + BM25 + RRF)
4. Hybrid + Cross-Encoder Reranker

The production ``chroma_db/`` is never used directly for retrieval. It is
copied to a temporary directory, and the retrieval modules are pointed at that
copy, so opening Chroma cannot modify the checked index. The script does not
call any LLM and does not report answer accuracy or refusal accuracy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from knowledge_config import (  # noqa: E402
    COLLECTION_NAME,
    DB_PATH,
    EMBEDDING_MODEL,
    RERANKER_MODEL,
)

DEFAULT_DATASET = ROOT / "eval" / "cnooc_eval_v1.json"
DEFAULT_OUTPUT_DIR = ROOT / "reports" / "eval"
CANDIDATE_BUDGET = 10
METRIC_KS = (1, 3, 5, 10)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_directory(path: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(item for item in path.rglob("*") if item.is_file())
    for item in files:
        digest.update(str(item.relative_to(path)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(item.read_bytes())
    return digest.hexdigest()


def read_index_metadata(db_path: Path, collection_name: str) -> dict:
    sqlite_path = db_path / "chroma.sqlite3"
    if not sqlite_path.is_file():
        raise FileNotFoundError(f"找不到 Chroma SQLite：{sqlite_path}")
    connection = sqlite3.connect(
        sqlite_path.resolve().as_uri() + "?mode=ro&immutable=1",
        uri=True,
    )
    try:
        collection = connection.execute(
            "SELECT name FROM collections WHERE name = ?",
            (collection_name,),
        ).fetchone()
        if collection is None:
            raise RuntimeError(f"Collection 不存在：{collection_name}")
        count = connection.execute(
            """
            SELECT COUNT(*)
            FROM embeddings e
            JOIN segments s ON s.id = e.segment_id
            JOIN collections c ON c.id = s.collection
            WHERE c.name = ?
            """,
            (collection_name,),
        ).fetchone()[0]
    finally:
        connection.close()
    return {"collection": collection_name, "chunk_count": int(count)}


def git_head() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return None


def score_for_method(item: dict, method: str) -> dict:
    keys = {
        "dense": ("distance",),
        "bm25": ("bm25_score",),
        "hybrid_rrf": ("rrf_score", "distance", "bm25_score"),
        "hybrid_rrf_reranker": ("rerank_score", "rrf_score", "distance", "bm25_score"),
    }[method]
    return {key: item[key] for key in keys if key in item}


def evaluate_method(method: str, retrieve_fn, questions: list[dict]) -> dict:
    records = []
    for question in questions:
        started = time.perf_counter()
        results = retrieve_fn(question["question"], CANDIDATE_BUDGET)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        expected = set(question.get("expected_chunk_ids", []))
        candidates = []
        for rank, item in enumerate(results, start=1):
            chunk_id = str(item.get("chunk_id", ""))
            candidates.append({
                "rank": rank,
                "chunk_id": chunk_id,
                "source": item.get("relative_path", ""),
                "page_start": item.get("page_start"),
                "page_end": item.get("page_end"),
                "is_relevant": chunk_id in expected,
                "scores": score_for_method(item, method),
            })

        relevant_ranks = [item["rank"] for item in candidates if item["is_relevant"]]
        first_rank = min(relevant_ranks) if relevant_ranks else None
        retrieved_expected = {
            item["chunk_id"] for item in candidates if item["is_relevant"]
        }
        missing = sorted(expected - retrieved_expected)
        if question["requires_abstention"]:
            failure_reason = None
        elif not relevant_ranks:
            failure_reason = "no_expected_chunk_in_top_10"
        elif missing:
            failure_reason = "partial_expected_chunks_missing"
        else:
            failure_reason = None

        records.append({
            "question_id": question["question_id"],
            "question": question["question"],
            "group": "abstention" if question["requires_abstention"] else "answerable",
            "category": question["category"],
            "difficulty": question["difficulty"],
            "expected_chunk_ids": sorted(expected),
            "expected_pages": question.get("expected_pages", []),
            "expected_document_ids": question.get("expected_document_ids", []),
            "retrieved_count": len(candidates),
            "candidate_budget": CANDIDATE_BUDGET,
            "first_relevant_rank": first_rank,
            "hit_at_1": first_rank == 1,
            "hit_at_3": first_rank is not None and first_rank <= 3,
            "hit_at_5": first_rank is not None and first_rank <= 5,
            "hit_at_10": first_rank is not None and first_rank <= 10,
            "recall_at_5": (
                len(retrieved_expected & set(
                    item["chunk_id"] for item in candidates[:5]
                )) / len(expected)
                if expected else None
            ),
            "recall_at_10": (
                len(retrieved_expected) / len(expected)
                if expected else None
            ),
            "missing_expected_chunk_ids": missing,
            "failure_reason": failure_reason,
            "elapsed_ms": elapsed_ms,
            "candidates": candidates,
        })
    return {"method": method, "records": records}


def summarize(method_result: dict, answerable_count: int) -> dict:
    records = [
        record for record in method_result["records"]
        if record["group"] == "answerable"
    ]
    if len(records) != answerable_count:
        raise ValueError("有答案题分母不一致")

    def mean(values):
        return sum(values) / len(values) if values else 0.0

    summary = {
        "method": method_result["method"],
        "answerable_denominator": answerable_count,
        "hit_at_1": mean([1.0 if record["hit_at_1"] else 0.0 for record in records]),
        "hit_at_3": mean([1.0 if record["hit_at_3"] else 0.0 for record in records]),
        "hit_at_5": mean([1.0 if record["hit_at_5"] else 0.0 for record in records]),
        "hit_at_10": mean([1.0 if record["hit_at_10"] else 0.0 for record in records]),
        "recall_at_5": mean([record["recall_at_5"] for record in records]),
        "recall_at_10": mean([record["recall_at_10"] for record in records]),
        "mrr_at_10": mean([
            1.0 / record["first_relevant_rank"]
            if record["first_relevant_rank"] else 0.0
            for record in records
        ]),
        "questions_with_less_than_10_candidates": sum(
            1 for record in records if record["retrieved_count"] < 10
        ),
        "min_retrieved_count": min(
            (record["retrieved_count"] for record in records), default=0
        ),
        "mean_elapsed_ms": round(mean([
            record["elapsed_ms"] for record in records
        ]), 1),
        "failure_count": sum(
            1 for record in records if record["failure_reason"] is not None
        ),
    }
    return summary


def build_markdown(report: dict) -> str:
    meta = report["run"]
    lines = [
        "# CNOOC 检索对照评测报告",
        "",
        f"- 数据集：`{meta['dataset_path']}`",
        f"- 数据集版本：`{meta['dataset_version']}`",
        f"- 数据集 SHA-256：`{meta['dataset_sha256']}`",
        f"- 索引快照 SHA-256：`{meta['index_snapshot_sha256']}`",
        f"- Collection：`{meta['collection']}`；Chunk 数：{meta['chunk_count']}",
        f"- Embedding：`{meta['embedding_model']}`",
        f"- Reranker：`{meta['reranker_model']}`",
        f"- 候选预算：{meta['candidate_budget']}；RRF k：60；BM25 分词：jieba",
        f"- 有答案题：{meta['answerable_count']}；无答案题：{meta['abstention_count']}",
        f"- 运行命令：`{meta['command']}`",
        f"- 运行时间：{meta['started_at']}（UTC），耗时 {meta['duration_seconds']} 秒",
        f"- 预热：每个方法先用“{meta['warmup_question']}”预热一次；下表耗时为预热后的单次调用平均，不含模型懒加载。预热耗时：{meta['warmup_seconds']}",
        f"- Python：{meta['python_version']}；平台：`{meta['platform']}`",
        f"- Git HEAD：`{meta['git_head']}`",
        "",
        "## 指标定义",
        "",
        "- **Hit@K**：Top-K 候选中至少有一个 Chunk ID 属于该题可接受相关集合的题目比例；分母为全部有答案题。",
        "- **Recall@K**：Top-K 候选中命中的可接受相关 Chunk 数 / 该题可接受相关 Chunk 总数；再对有答案题取平均。多证据题按相关集合计算。",
        "- **MRR@10**：首个相关 Chunk 排名倒数的平均值；未命中记 0；分母为全部有答案题。",
        "- 所有方法使用相同题目、相同索引快照和 10 个候选预算。实际返回数少于 10 的题目已在逐题记录中标记；本报告不虚构未返回的候选。",
        "- 无答案题不进入上述检索指标分母；本任务没有对全部题目运行 LLM，因此不报告答案准确率或拒答率。",
        "",
        "## 汇总（有答案题，分母 = {answerable_count}）".format(
            answerable_count=meta["answerable_count"]
        ),
        "",
        "| 方法 | Hit@1 | Hit@3 | Hit@5 | Hit@10 | Recall@5 | Recall@10 | MRR@10 | 平均耗时 ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in report["summary"]:
        lines.append(
            "| {method} | {hit1:.2%} | {hit3:.2%} | {hit5:.2%} | {hit10:.2%} | "
            "{recall5:.2%} | {recall10:.2%} | {mrr:.4f} | {latency:.1f} |".format(
                method=item["method"],
                hit1=item["hit_at_1"],
                hit3=item["hit_at_3"],
                hit5=item["hit_at_5"],
                hit10=item["hit_at_10"],
                recall5=item["recall_at_5"],
                recall10=item["recall_at_10"],
                mrr=item["mrr_at_10"],
                latency=item["mean_elapsed_ms"],
            )
        )
    lines += [
        "",
        "## 无答案题",
        "",
        f"- 共 {meta['abstention_count']} 道；未做 LLM 全量评测，因此不计算拒答准确率。",
        "- 逐题候选仍保存在 JSON 中，供后续人工检查；无答案题不混入有答案检索指标。",
        "",
        "## 失败案例（有答案题）",
        "",
    ]
    failures = []
    for method_result in report["methods"]:
        for record in method_result["records"]:
            if record["group"] != "answerable":
                continue
            if record["failure_reason"] is None:
                continue
            failures.append((method_result["method"], record))
    if not failures:
        lines.append("无。")
    else:
        lines.append("| 方法 | 题目 | 类别 | 首个相关排名 | 失败原因 | 缺失 Chunk |")
        lines.append("|---|---|---|---:|---|---|")
        for method, record in failures:
            lines.append(
                "| {method} | {qid} {question} | {category} | {rank} | {reason} | {missing} |".format(
                    method=method,
                    qid=record["question_id"],
                    question=record["question"].replace("|", "\\|"),
                    category=record["category"],
                    rank=record["first_relevant_rank"] if record["first_relevant_rank"] else "未命中",
                    reason=record["failure_reason"],
                    missing=", ".join(record["missing_expected_chunk_ids"]) or "—",
                )
            )
    lines += [
        "",
        "## 逐题候选",
        "",
        "逐题、逐方法的候选 Chunk ID、来源、页码、名次、分数与命中状态保存在同目录 JSON 的 `methods[].records[]` 中。",
        "",
    ]
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dataset_path = args.dataset.resolve()
    if not dataset_path.is_file():
        raise FileNotFoundError(f"找不到数据集：{dataset_path}")
    dataset_bytes = dataset_path.read_bytes()
    dataset = json.loads(dataset_bytes)
    questions = dataset["questions"]
    answerable = [q for q in questions if not q["requires_abstention"]]
    abstention = [q for q in questions if q["requires_abstention"]]
    if len(questions) != len(answerable) + len(abstention):
        raise ValueError("题目分组不一致")
    if len(answerable) < 20 or len(abstention) < 5:
        raise ValueError("数据集至少需要 20 道有答案题和 5 道无答案题")

    index_metadata = read_index_metadata(DB_PATH, COLLECTION_NAME)
    index_hash = sha256_directory(DB_PATH)
    started_at = datetime.now(timezone.utc).isoformat()
    run_started = time.perf_counter()

    temp_root = Path(tempfile.mkdtemp(prefix="cnooc_eval_chroma_"))
    db_copy = temp_root / COLLECTION_NAME
    try:
        shutil.copytree(DB_PATH, db_copy)
        import retrieval
        import hybrid_retrieval

        retrieval.DB_PATH = db_copy
        retrieval._collection = None
        hybrid_retrieval._corpus = None
        hybrid_retrieval._bm25 = None

        methods = OrderedDict([
            ("dense", lambda question, k: retrieval.retrieve_top_k(question, k=k)),
            ("bm25", lambda question, k: hybrid_retrieval.retrieve_bm25(question, k=k)),
            ("hybrid_rrf", lambda question, k: hybrid_retrieval.retrieve_hybrid(question, k=k)),
            (
                "hybrid_rrf_reranker",
                lambda question, k: hybrid_retrieval.retrieve_with_reranker(
                    question, k=k, candidate_k=k
                ),
            ),
        ])

        if not answerable:
            raise ValueError("数据集没有有答案题，无法预热检索模型")
        warmup_question = answerable[0]["question"]
        warmup_seconds = {}
        method_results = []
        summaries = []
        for method_name, retrieve_fn in methods.items():
            print(f"[eval] {method_name} warmup ...", flush=True)
            warmup_started = time.perf_counter()
            retrieve_fn(warmup_question, CANDIDATE_BUDGET)
            warmup_seconds[method_name] = round(
                time.perf_counter() - warmup_started, 1
            )
            print(f"[eval] {method_name} ...", flush=True)
            result = evaluate_method(method_name, retrieve_fn, questions)
            method_results.append(result)
            summaries.append(summarize(result, len(answerable)))
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    duration = round(time.perf_counter() - run_started, 1)
    report = {
        "run": {
            "dataset_path": str(dataset_path.relative_to(ROOT))
            if dataset_path.is_relative_to(ROOT) else str(dataset_path),
            "dataset_version": dataset["dataset_version"],
            "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
            "index_snapshot_sha256": index_hash,
            "index_source_path": str(DB_PATH),
            "collection": index_metadata["collection"],
            "chunk_count": index_metadata["chunk_count"],
            "embedding_model": EMBEDDING_MODEL,
            "reranker_model": RERANKER_MODEL,
            "candidate_budget": CANDIDATE_BUDGET,
            "rrf_k": 60,
            "bm25_tokenizer": "jieba",
            "answerable_count": len(answerable),
            "abstention_count": len(abstention),
            "started_at": started_at,
            "duration_seconds": duration,
            "command": " ".join(sys.argv),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "git_head": git_head(),
            "warmup_question": warmup_question,
            "warmup_seconds": warmup_seconds,
            "llm_called": False,
            "production_chroma_written": False,
        },
        "summary": summaries,
        "methods": method_results,
        "abstention_questions": [
            {
                "question_id": q["question_id"],
                "question": q["question"],
                "category": q["category"],
                "abstention_basis": q.get("abstention_basis", ""),
            }
            for q in abstention
        ],
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "cnooc_retrieval_eval_v1.json"
    md_path = args.output_dir / "cnooc_retrieval_eval_v1.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(build_markdown(report), encoding="utf-8")
    print(f"[eval] JSON: {json_path}")
    print(f"[eval] Markdown: {md_path}")
    for item in summaries:
        print(
            f"[eval] {item['method']}: Hit@1={item['hit_at_1']:.2%} "
            f"Hit@3={item['hit_at_3']:.2%} Hit@10={item['hit_at_10']:.2%} "
            f"Recall@10={item['recall_at_10']:.2%} MRR@10={item['mrr_at_10']:.4f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
