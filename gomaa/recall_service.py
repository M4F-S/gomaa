"""Read-only recall service: a small HTTP endpoint over the Gomaa store.

Why this exists
---------------
An agent that wants memory **during** a conversation cannot always import this package: the
Hermes gateway venv, for instance, has no psycopg2, no numpy and no sentence-transformers. The
service runs in the process that *does* have the memory stack (the MCP server venv, a systemd
unit, a container) and exposes a bounded, JSON-only endpoint to anything that can make an HTTP
call — including non-Python agents.

Design rules that are not optional
----------------------------------
* **Read-only.** `UnifiedMemorySystem.recall()` bumps ``access_count`` on every row it returns.
  A per-turn caller would turn popularity into a function of how often a topic was mentioned,
  poisoning ACTR ranking and decay. This module queries the stores directly and never writes.
* **Shared memory off by default.** Measured on a live 260-note store: generic shared policies
  outrank specific project notes, and ``include_shared=True`` halved the usable top-3 result.
* **Bounded.** A hard character budget, a bounded candidate window, ``[]``/empty block on any
  error. A dead store must look like "nothing to recall", never like a failed request.
* **Measurable.** Every query logs the titles it injected (never the content), so retrieval can
  be scored from the service's own log.

Run it::

    python -m gomaa.recall_service --host 127.0.0.1 --port 8790

Endpoints::

    GET  /health                      -> {"ok": true, "notes": <active count>}
    POST /recall {"query": str, "top_k": 4, "budget_chars": 1000, "include_shared": false}
                                      -> {"ok": true, "block": str, "titles": [...], "took_ms": float}
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence

from . import recall_rank

logger = logging.getLogger(__name__)

RRF_K = 60
MAX_CONTENT_CHARS = 320
EMB_CACHE_MAX = 256
#: Rooms whose notes win queries by length rather than relevance (measured, not guessed).
GENERIC_ROOMS = frozenset({"general", "user-preferences", "sessions"})
#: A question shaped like this is *about* preferences, so the generic-room penalty is wrong.
PREFERENCE_HINTS = (
    "prefer", "preference", "how should", "how do you", "convention", "style",
    "remember", "always", "never", "you must", "you should",
)
#: Notes that describe a moment in time. When one is old it is misinformation, not weak evidence.
PERISHABLE_TAGS = frozenset({"live-state", "live_state", "snapshot", "status"})


def _is_perishable(row: Dict[str, Any]) -> bool:
    title = (row.get("title") or "").lower()
    tags = {str(t).lower() for t in (row.get("tags") or [])}
    return bool(tags & PERISHABLE_TAGS) or "live state" in title or "live-state" in title


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def _ranks(rows: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    return {_norm(r.get("title")): i for i, r in enumerate(rows, 1) if r.get("title")}


def rank_rows(
    semantic_rows: Sequence[Dict[str, Any]],
    keyword_rows: Sequence[Dict[str, Any]],
    shared_rows: Sequence[Dict[str, Any]] = (),
    *,
    query: str = "",
    top_k: int = 4,
    now: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Delegate to :func:`gomaa.recall_rank.rank_rows` — one ranker, not two.

    This module used to carry its own copy of the fusion and penalty logic; the two drifted
    (different perishable rules, different penalties), so a benchmark of one measured nothing
    about the other. The signature is kept for callers and tests.
    """
    return recall_rank.rank_rows(
        semantic_rows, keyword_rows, shared_rows, query=query, top_k=top_k, now=now
    )


def format_block(rows: Sequence[Dict[str, Any]], budget_chars: int = 1000,
                 max_content_chars: int = MAX_CONTENT_CHARS) -> str:
    """Render rows via :mod:`gomaa.recall_rank`; returns the bullet block (no header)."""
    block, _titles = recall_rank.format_block(list(rows), budget_chars)
    return block


class RecallService:
    """Thin read-only layer over :class:`gomaa.core.UnifiedMemorySystem`."""

    def __init__(self, memory: Any, *, top_k: int = 4, budget_chars: int = 1000,
                 include_shared: bool = False, log_path: Optional[str] = None) -> None:
        self.memory = memory
        self.top_k = top_k
        self.budget_chars = budget_chars
        self.include_shared = include_shared
        self.log_path = log_path
        self._emb_cache: Dict[str, Any] = {}
        self._lock = threading.Lock()

    # -- internals ---------------------------------------------------------

    def _embed(self, query: str):
        key = query.strip().lower()
        if key in self._emb_cache:
            return self._emb_cache[key]
        vector = self.memory.embedder.embed_query(query)
        if len(self._emb_cache) >= EMB_CACHE_MAX:
            self._emb_cache.clear()
        self._emb_cache[key] = vector
        return vector

    def _log(self, query: str, titles: List[str], took_ms: float, chars: int) -> None:
        if not self.log_path:
            return
        try:
            with open(self.log_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps({
                    "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "query": query[:200], "titles": titles,
                    "latency_ms": round(took_ms, 1), "chars": chars,
                }, ensure_ascii=False) + "\n")
        except OSError:
            pass

    # -- public API --------------------------------------------------------

    def recall(self, query: str, *, top_k: Optional[int] = None,
               budget_chars: Optional[int] = None,
               include_shared: Optional[bool] = None) -> Dict[str, Any]:
        started = time.perf_counter()
        query = (query or "").strip()
        top_k = top_k or self.top_k
        budget = budget_chars or self.budget_chars
        shared = self.include_shared if include_shared is None else bool(include_shared)
        if len(query) < 3:
            return {"ok": True, "block": "", "titles": [], "count": 0, "took_ms": 0.0}

        wide = max(top_k * 3, 12)
        embedding = self._embed(query)
        embedder_id = getattr(self.memory.embedder, "embedder_id", None)

        semantic = self.memory.db.search_semantic(
            embedding, wide, None, scope=None, embedder_id=embedder_id)
        keyword = self.memory.db.search_keyword(query, wide, scope=None)
        shared_rows: Sequence[Dict[str, Any]] = ()
        if shared and getattr(self.memory, "shared_db", None) is not None:
            try:
                shared_rows = self.memory.shared_db.search_semantic(
                    embedding, wide, None, scope=None, embedder_id=embedder_id)
            except Exception as exc:                      # pragma: no cover - store specific
                logger.warning("shared search failed: %s", exc)

        with self._lock:
            rows = rank_rows(semantic, keyword, shared_rows, query=query, top_k=top_k)
        block = format_block(rows, budget)
        titles = [row.get("title") for row in rows][:top_k]
        took_ms = (time.perf_counter() - started) * 1000.0
        self._log(query, [t for t in titles if t], took_ms, len(block))
        return {"ok": True, "block": block, "titles": titles,
                "count": len(rows), "took_ms": round(took_ms, 1)}

    def health(self) -> Dict[str, Any]:
        notes = -1
        try:
            notes = int(self.memory.db.count_notes())
        except Exception:
            pass
        return {"ok": True, "notes": notes}


def build_handler(service: RecallService):
    """Return a ``BaseHTTPRequestHandler`` subclass wired to *service*."""
    from http.server import BaseHTTPRequestHandler

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args, **kwargs):  # keep stdout clean for supervisors
            return

        def _send(self, code: int, payload: Dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode()
            try:
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass                                  # caller's own timeout fired first

        def do_GET(self):                             # noqa: N802
            if self.path.split("?")[0] in ("/health", "/healthz"):
                self._send(200, service.health())
            else:
                self._send(404, {"ok": False, "error": "not found"})

        def do_POST(self):                            # noqa: N802
            if self.path.split("?")[0] != "/recall":
                self._send(404, {"ok": False, "error": "not found"})
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
                payload = json.loads(self.rfile.read(length) or b"{}")
                result = service.recall(
                    payload.get("query") or "",
                    top_k=payload.get("top_k"),
                    budget_chars=payload.get("budget_chars"),
                    include_shared=payload.get("include_shared"),
                )
            except Exception as exc:                  # never 500 a caller mid-turn
                logger.warning("recall failed: %s", exc)
                result = {"ok": True, "block": "", "titles": [], "count": 0,
                          "took_ms": 0.0, "error": str(exc)[:200]}
            self._send(200, result)

    return Handler


def serve(memory: Any, host: str = "127.0.0.1", port: int = 8790, **kwargs) -> None:
    """Blocking server. ``memory`` is injected so callers own the store configuration."""
    from http.server import ThreadingHTTPServer

    service = RecallService(memory, **kwargs)
    handler = build_handler(service)
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    logger.info("recall service listening on %s:%s", host, port)
    server.serve_forever()


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Read-only Gomaa recall HTTP service")
    parser.add_argument("--host", default=os.environ.get("GOMAA_RECALL_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("GOMAA_RECALL_PORT", "8790")))
    parser.add_argument("--top-k", type=int, default=int(os.environ.get("GOMAA_RECALL_TOP_K", "4")))
    parser.add_argument("--budget-chars", type=int, default=int(os.environ.get("GOMAA_RECALL_BUDGET", "1000")))
    parser.add_argument("--include-shared", action="store_true",
                        help="also search the shared fleet store (off by default: it outranks project notes)")
    parser.add_argument("--log", default=os.environ.get("GOMAA_RECALL_LOG", ""),
                        help="JSONL file receiving one line per query (titles only)")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] gomaa-recall: %(message)s")

    from gomaa.core import UnifiedMemorySystem
    memory = UnifiedMemorySystem()
    serve(memory, host=args.host, port=args.port, top_k=args.top_k,
          budget_chars=args.budget_chars, include_shared=args.include_shared,
          log_path=args.log or None)
    return 0


if __name__ == "__main__":                            # pragma: no cover
    raise SystemExit(main())
