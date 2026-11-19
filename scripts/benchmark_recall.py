"""Score recall quality mechanically: hit@1 / hit@k / misses, plus latency percentiles.

Two modes:

* ``--service`` — query a running recall service (measures what an agent actually receives).
* ``--store``   — query the store in-process through the same ranking code the service uses.

Questions live in a JSON file (one object per line or a list), each ``{"question": ...,
"expect": "<substring of the note title>"}``. The question must be a *paraphrase* — a title
match proves nothing.

    python scripts/benchmark_recall.py questions.json --service http://127.0.0.1:8790 --top-k 4
    python scripts/benchmark_recall.py questions.json --store

Environment for ``--store``: MEMORY_DB_DSN / MEMORY_VAULT_PATH (and optionally MEMORY_SHARED_DSN).
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from typing import Any, Dict, List


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def load_questions(path: str) -> List[Dict[str, str]]:
    with open(path, encoding="utf-8") as handle:
        raw = handle.read().strip()
    if not raw:
        return []
    if raw.lstrip().startswith("["):
        data = json.loads(raw)
    else:
        data = [json.loads(line) for line in raw.splitlines() if line.strip()]
    questions = []
    for item in data:
        question, expect = item.get("question"), item.get("expect")
        if question and expect:
            questions.append({"question": question, "expect": expect})
    return questions


def _matches(titles: List[str], expect: str) -> bool:
    want = _norm(expect)
    return any(want in _norm(title) or _norm(title) in want for title in titles)


def query_service(url: str, question: str, top_k: int) -> Dict[str, Any]:
    import urllib.request

    request = urllib.request.Request(
        url.rstrip("/") + "/recall",
        data=json.dumps({"query": question, "top_k": top_k}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read())


def query_store(question: str, top_k: int) -> Dict[str, Any]:
    from gomaa.core import UnifiedMemorySystem
    from gomaa.recall_service import RecallService

    memory = UnifiedMemorySystem()
    service = RecallService(memory, top_k=top_k)
    started = time.perf_counter()
    result = service.recall(question, top_k=top_k)
    result["took_ms"] = round((time.perf_counter() - started) * 1000.0, 1)
    return result


def run(questions: List[Dict[str, str]], *, top_k: int, service_url: str = "", store: bool = False) -> int:
    hits1 = hitsk = 0
    latencies: List[float] = []
    misses: List[str] = []
    for item in questions:
        question, expect = item["question"], item["expect"]
        result = query_store(question, top_k) if store else query_service(service_url, question, top_k)
        titles = [t for t in (result.get("titles") or []) if t]
        latencies.append(float(result.get("took_ms") or 0.0))
        position = next((i for i, title in enumerate(titles, 1)
                         if _norm(expect) in _norm(title) or _norm(title) in _norm(expect)), None)
        if position == 1:
            hits1 += 1
        if position:
            hitsk += 1
        else:
            misses.append(question)
        print(f"{'hit@%d' % position if position else 'MISS':>7}  {question[:70]}")

    total = len(questions) or 1
    ordered = sorted(latencies)
    p50 = statistics.median(ordered) if ordered else 0.0
    p95 = ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))] if ordered else 0.0
    print(f"\nit was: hit@1 {hits1}/{total} | hit@{top_k} {hitsk}/{total} | "
          f"p50 {p50:.0f} ms | p95 {p95:.0f} ms")
    if misses:
        print("misses:")
        for question in misses:
            print(f"  - {question}")
    # Exit code: 0 when every expected note was injected, 1 otherwise (CI-friendly).
    return 0 if hitsk == total else 1


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("questions", help="JSON or JSONL file of {question, expect} objects")
    parser.add_argument("--service", default="", help="base URL of a running recall service")
    parser.add_argument("--store", action="store_true", help="query the store in-process instead")
    parser.add_argument("--top-k", type=int, default=4)
    args = parser.parse_args(argv)

    questions = load_questions(args.questions)
    if not questions:
        print("no questions loaded", file=sys.stderr)
        return 2
    if not args.service and not args.store:
        parser.error("choose --service URL or --store")
    return run(questions, top_k=args.top_k, service_url=args.service, store=args.store)


if __name__ == "__main__":
    raise SystemExit(main())
