"""Gomaa recall service — local, read-only HTTP endpoint for per-turn memory recall.

Ranking lives in ``gomaa.recall_rank`` (one implementation, shared with the package) so a
benchmark measures the behaviour agents actually get.

Design constraints (measured):
  * include_shared defaults to FALSE — fleet policies were burying project notes;
  * every store call passes ``touch=False``: a per-turn reader must not inflate access_count,
    which feeds ACT-R ranking and decay (measured: 99 of 207 notes touched in 3 days);
  * bounded: internal budget, [] on any error, never raises to the caller;
  * logs the injected titles and the client kind per query, so provider traffic is separable
    from benchmark probes.

Run: /opt/data/mcp-servers/venv/bin/python /opt/data/scripts/gomaa_recall_service.py
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LAUNCHER = "/opt/data/mcp-servers/obsidian_memory_mcp.py"
SERVICE_LOG = "/opt/data/logs/gomaa-recall.jsonl"
HOST, PORT = "127.0.0.1", 8790

logging.basicConfig(stream=sys.stderr, level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] gomaa-recall: %(message)s")
log = logging.getLogger("gomaa-recall")


def _launcher_env(key: str) -> str:
    """Read the DSN/vault values from the MCP launcher — one source of truth, never duplicated here."""
    try:
        src = open(LAUNCHER, encoding="utf-8").read()
    except OSError as exc:
        log.error("cannot read launcher %s: %s", LAUNCHER, exc)
        return ""
    m = re.search(r'os\.environ\["%s"\]\s*=\s*"([^"]+)"' % re.escape(key), src)
    return m.group(1) if m else ""


# Env must be set before gomaa is imported (store/embedder read it at construction).
for _k in ("MEMORY_DB_DSN", "MEMORY_SHARED_DSN", "MEMORY_VAULT_PATH", "MEMORY_AGENT_NAME", "MEMORY_EMBED_URL"):
    _v = os.environ.get(_k) or _launcher_env(_k)
    if _v:
        os.environ[_k] = _v
os.environ.setdefault("MEMORY_REQUIRE_POSTGRES", "true")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

sys.path.insert(0, "/opt/data/gomaa-live")
from gomaa.core import UnifiedMemorySystem  # noqa: E402
from gomaa import recall_rank  # noqa: E402

MEM = UnifiedMemorySystem()
LOCK = threading.Lock()

EMB_CACHE: dict = {}
EMB_CACHE_MAX = 256


def _embed(query: str):
    """Memoised query embedding: the encoder is the whole latency budget on a busy host."""
    key = query.strip().lower()
    if key in EMB_CACHE:
        return EMB_CACHE[key]
    vec = MEM.embedder.embed_query(query)
    if len(EMB_CACHE) >= EMB_CACHE_MAX:
        EMB_CACHE.clear()
    EMB_CACHE[key] = vec
    return vec


def _log_query(query, titles, latency_ms, chars, client):
    try:
        os.makedirs(os.path.dirname(SERVICE_LOG), exist_ok=True)
        with open(SERVICE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "msg_id": os.getpid(),
                "client": client,
                "query": (query or "")[:200], "titles": titles,
                "latency_ms": round(latency_ms, 1), "chars": chars,
            }, ensure_ascii=False) + "\n")
    except Exception:
        pass


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # keep stdout clean
        return

    def _send(self, code: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode()
        try:
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            # The provider's read timeout fired first — the answer is late, not wrong.
            pass

    def do_GET(self):
        if self.path.split("?")[0] in ("/health", "/healthz"):
            try:
                n = MEM.db.count_notes() if hasattr(MEM.db, "count_notes") else -1
            except Exception:
                n = -1
            self._send(200, {"ok": True, "notes": n, "agent": os.environ.get("MEMORY_AGENT_NAME")})
        else:
            self._send(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        if self.path.split("?")[0] != "/recall":
            self._send(404, {"ok": False, "error": "not found"})
            return
        t0 = time.perf_counter()
        try:
            length = int(self.headers.get("Content-Length") or 0)
            req = json.loads(self.rfile.read(length) or b"{}")
            query = (req.get("query") or "").strip()
            top_k = max(1, min(int(req.get("top_k", 5)), 12))
            budget = max(80, min(int(req.get("budget_chars", 1200)), 4000))
            include_shared = bool(req.get("include_shared", False))
            client = str(req.get("client") or "unknown")[:24]
            if len(query) < 3:
                self._send(200, {"ok": True, "block": "", "titles": [], "took_ms": 0.0})
                return
            emb = _embed(query)
            eid = getattr(MEM.embedder, "embedder_id", None)
            with LOCK:
                rows = recall_rank.hybrid(MEM.db, MEM.shared_db, query, emb,
                                          top_k=top_k, include_shared=include_shared,
                                          embedder_id=eid)
            block, titles = recall_rank.format_block(rows, budget)
            took = (time.perf_counter() - t0) * 1000.0
            _log_query(query, titles, took, len(block), client)
            self._send(200, {"ok": True, "block": block, "titles": titles,
                             "took_ms": round(took, 1), "count": len(rows)})
        except Exception as exc:
            log.warning("recall failed: %s", exc)
            self._send(200, {"ok": True, "block": "", "titles": [], "took_ms": 0.0, "error": str(exc)[:200]})


if __name__ == "__main__":
    log.info("ready: agent=%s vault=%s", os.environ.get("MEMORY_AGENT_NAME"),
             os.environ.get("MEMORY_VAULT_PATH"))
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    srv.daemon_threads = True
    srv.serve_forever()
