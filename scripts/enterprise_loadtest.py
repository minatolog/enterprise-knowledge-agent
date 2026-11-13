"""Bounded load test. Health by default; query mode requires explicit opt-in."""
import argparse
import concurrent.futures
import json
import statistics
import time
from pathlib import Path

import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8030")
    parser.add_argument("--requests", type=int, default=20)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--query", help="Explicitly enable model-billed query load")
    parser.add_argument("--token-file", type=Path)
    parser.add_argument("--output", type=Path, default=Path(".enterprise/loadtest.json"))
    args = parser.parse_args()
    if not (1 <= args.requests <= 1000 and 1 <= args.workers <= 32):
        parser.error("requests 1..1000; workers 1..32")
    if args.query and not args.token_file:
        parser.error("query mode needs a token file")
    headers = {"Authorization": "Bearer " + args.token_file.read_text().strip()} if args.token_file else {}
    def call(_):
        started = time.perf_counter()
        try:
            if args.query:
                response = httpx.post(args.url + "/api/v2/query", json={"question": args.query}, headers=headers, timeout=120)
            else:
                response = httpx.get(args.url + "/health", timeout=10)
            return time.perf_counter() - started, response.status_code
        except httpx.HTTPError:
            return time.perf_counter() - started, 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        rows = list(executor.map(call, range(args.requests)))
    durations = sorted(row[0] for row in rows)
    result = dict(mode="query" if args.query else "health_only", requests=len(rows), workers=args.workers,
        errors=sum(status != 200 for _, status in rows), p50_seconds=statistics.median(durations),
        p95_seconds=durations[min(len(rows) - 1, int(len(rows) * 0.95))])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
