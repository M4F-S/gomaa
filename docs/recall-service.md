# Recall service — memory during a conversation, not just at its start

`gomaa/recall_service.py` is a small read-only HTTP endpoint over the store. It exists because the
process that *wants* memory is often not the process that *has* the stack: a Hermes gateway venv,
for example, ships no psycopg2, no numpy and no sentence-transformers, and installing a second copy
of this package there is how upgrades break.

```
GET  /health            -> {"ok": true, "notes": <active notes>}
POST /recall            {"query": "...", "top_k": 4, "budget_chars": 1000, "include_shared": false}
                        -> {"ok": true, "block": "- title (wing/room): body…", "titles": [...],
                            "count": 4, "took_ms": 328.4}
```

Run it where the store already lives:

```bash
python -m gomaa.recall_service --host 127.0.0.1 --port 8790 --top-k 4 --budget-chars 1000 \
    --log /var/log/gomaa-recall.jsonl
```

## Four rules, each learned by measuring

1. **Read-only, or it corrupts ranking.** `UnifiedMemorySystem.recall()` updates `access_count` for
   every row it returns. A caller that runs on every turn would make popularity a function of how
   often a topic was mentioned, and ACTR ranking and decay both read that column. This service
   calls `search_semantic` / `search_keyword` directly and never writes.
2. **`include_shared` defaults to false.** On a live 260-note store the shared fleet policies
   outranked the specific project note they were related to: hit@3 was 2/10 with shared rows and
   5/10 without. The flag exists; the default must not.
3. **Generic rooms need a structural penalty.** Unscoped hybrid retrieval let `general`,
   `user-preferences` and `sessions` notes win on length. The re-ranker subtracts 2.0 for those
   rooms unless the question is preference-shaped, subtracts 3.0 for `shared`/`fleet`, and adds 2.5
   when the question names the note's room.
4. **The budget is a contract.** `budget_chars` is hard. If it is smaller than one bullet, the
   service returns the beginning of the best note rather than an empty string — "no memory" and
   "memory we could not fit" must not look the same to the caller.

## Client side: the Hermes memory provider

Hermes exposes a per-turn hook (`agent/memory_provider.py`): `queue_prefetch()` runs after a turn,
`prefetch()` runs before the next model call and returns what the model sees. Two properties of
that hook matter here:

* `prefetch()` **blocks the turn** (8 s ceiling) and is skipped entirely while a previous call is
  still running, so the query belongs in `queue_prefetch`, and `prefetch` should return a cache.
* the returned block is stamped into the user row and **replayed on every later request** for the
  rest of the session. Injecting 800 tokens per turn is not 800 tokens once; dedupe titles already
  injected and keep the block near 300 tokens.

Reference client: `plugins/memory/gomaa/` (HTTP only, `requests`, no store dependencies).

## Measuring it

`scripts/benchmark_recall.py` scores a question set against a running service or the store itself:

```bash
python scripts/benchmark_recall.py questions.json --service http://127.0.0.1:8790 --top-k 4
python scripts/benchmark_recall.py questions.json --store
```

Questions must be paraphrases of a note's content with the note title as `expect`; a title-shaped
question proves nothing. Report **hit@1 / hit@k / p50 / p95**, and re-run the same file unchanged
after any ranking change.

Live numbers from a 260-note store (10 questions, `old_db`):

| variant | hit@1 | in the injected set |
|---|---|---|
| hybrid, shared on, top 3 | 2/10 | 2/10 |
| hybrid, shared off, top 3 | 2/10 | 5/10 |
| hybrid, shared off, top 5 | 3/10 | 7/10 |
| this service, top 5 | — | 7/10 (p50 328 ms) |

The three misses are not retrieval failures: two are one-line identity/preference facts that lose
to longer notes by design (they belong in the system prompt), one is a genuine ranking miss.

## Operating notes

* Cold start is the expensive part (loading the encoder): ~19 s on a small VPS. Supervise with a
  watchdog whose readiness window is at least twice the measured cold start.
* Start the service **outside** the consumer's process group. A service started as a child of the
  agent dies at the next agent restart, and the first thing the watchdog sees is a dead service.
* The provider should time out fast and fail open (empty block). Measured cold queries ranged
  0.3–1.4 s across hosts; a 0.9 s client timeout silently dropped real answers.
