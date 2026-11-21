"""Gomaa recall service — local, read-only HTTP endpoint for per-turn memory recall.

Used by:
  * the Hermes memory provider plugin (`plugins/gomaa`), which cannot import psycopg2 or gomaa
    inside the gateway venv;
  * later, the native C agents (Belya/Almaz), which have no plugin API at all.

Design constraints (measured, see REVIEW-provider-per-turn.md):
  * include_shared defaults to FALSE — fleet policies were burying project notes (hit@3 2/10 -> 5/10);
  * hybrid = semantic + keyword RRF computed here, NOT UnifiedMemorySystem.recall(), because recall()
    bumps access_count on every returned row and a per-turn caller would poison ACTR ranking/decay;
  * bounded: internal budget, [] on any error, never raises to the caller;
  * logs injected titles per query (titles only, no content) so the provider is measurable.

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

MEM = UnifiedMemorySystem()
LOCK = threading.Lock()

# --- ranking shape -------------------------------------------------------------------------
# Generic rooms that won the benchmark by length rather than relevance.
GENERIC_ROOMS = {"general", "user-preferences", "sessions"}
PREFERENCE_HINTS = ("prefer", "preference", "how should", "how do you", "convention", "style",
                    "remember", "always", "never", "you must", "you should")
RRF_K = 60
MAX_CONTENT_CHARS = 320
PERISHABLE_TAGS = {"live-state", "live_state", "snapshot", "status"}


def _is_perishable(r):
    title = (r.get("title") or "").lower()
    tags = {str(t).lower() for t in (r.get("tags") or [])}
    return bool(tags & PERISHABLE_TAGS) or "live state" in title or "live-state" in title

EMB_CACHE: dict = {}
EMB_CACHE_MAX = 256


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _ranked(rows):
    return {_norm(r.get("title")): i for i, r in enumerate(rows, 1) if r.get("title")}


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


def hybrid(query: str, top_k: int, include_shared: bool):
    """Semantic + keyword RRF over the private store (+ shared when asked). No writes."""
    emb = _embed(query)
    eid = getattr(MEM.embedder, "embedder_id", None)
    wide = max(top_k * 3, 12)

    sem = MEM.db.search_semantic(emb, wide, None, scope=None, embedder_id=eid)
    kw = MEM.db.search_keyword(query, wide, scope=None)
    earm = _ranked(sem)
    kwarm = _ranked(kw)
    by_title = {}
    for r in sem + kw:
        t = _norm(r.get("title"))
        if t and t not in by_title:
            by_title[t] = dict(r, _rrf=0.0, _sem=0.0, _kw=0.0)
    for t, row in by_title.items():
        if t in earm:
            row["_rrf"] += 1.0 / (RRF_K + earm[t])
            row["_sem"] = float(row.get("score") or 0.0)
        if t in kwarm:
            row["_rrf"] += 1.0 / (RRF_K + kwarm[t])
            row["_kw"] = 1.0

    if include_shared and MEM.shared_db is not None:
        try:
            shared = MEM.shared_db.search_semantic(emb, wide, None, scope=None, embedder_id=eid)
            for i, r in enumerate(shared, 1):
                t = _norm(r.get("title"))
                if t and t not in by_title:
                    by_title[t] = dict(r, _rrf=1.0 / (RRF_K + i), _sem=float(r.get("score") or 0), _kw=0.0)
        except Exception as exc:
            log.warning("shared search failed: %s", exc)

    pref_query = any(h in (query or "").lower() for h in PREFERENCE_HINTS)
    q = _norm(query)
    now = datetime.now(timezone.utc)
    rows = []
    for t, r in by_title.items():
        tags = {str(x).lower() for x in (r.get("tags") or [])}
        if r.get("superseded_by") or "probe" in tags:
            continue                          # history or test debris, not context
        score = r["_rrf"] * 100.0
        wing, room = (r.get("wing") or ""), (r.get("room") or "")
        if wing == "fleet":
            score -= 3.0                      # fleet policy: already in the system prompt
        if room in GENERIC_ROOMS and not pref_query:
            score -= 2.0                      # generic room beating a specific project note
        if room and _norm(room) in q:
            score += 2.5                      # message names the room's subject
        if wing and _norm(wing) in q:
            score += 1.5
        age_d = None
        try:                                  # recency: small tie-break only
            created = r.get("created_at") or r.get("updated_at")
            if created:
                age_d = max((now - created.replace(tzinfo=timezone.utc)).days, 0) if created.tzinfo is None \
                    else max((now - created).days, 0)
                score += 1.0 / (1.0 + age_d / 30.0)
        except Exception:
            age_d = None
        # Old snapshots are misinformation, not weak evidence.
        if age_d is not None and _is_perishable(r):
            score -= min(4.0, age_d * 0.2)
        r["_score"] = score
        rows.append(r)
    rows.sort(key=lambda x: x["_score"], reverse=True)
    return rows[:top_k]


def format_block(rows, budget_chars: int) -> str:
    out, used = [], 0
    for r in rows:
        title = (r.get("title") or "").strip()
        body = re.sub(r"\s+", " ", (r.get("content") or "")).strip()
        if len(body) > MAX_CONTENT_CHARS:
            body = body[:MAX_CONTENT_CHARS].rstrip() + "…"
        scope = "/".join(p for p in (r.get("wing"), r.get("room")) if p)
        as_of = ""
        created = r.get("created_at") or r.get("updated_at")
        if created and _is_perishable(r):
            as_of = f" [as of {created.date().isoformat()}]"
        line = f"- {title}{as_of}" + (f" ({scope})" if scope else "") + (f": {body}" if body else "")
        if used + len(line) + 1 > budget_chars:
            break
        out.append(line)
        used += len(line) + 1
    return "\n".join(out)


def _log_query(query, titles, latency_ms, chars):
    try:
        os.makedirs(os.path.dirname(SERVICE_LOG), exist_ok=True)
        with open(SERVICE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
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
            if len(query) < 3:
                self._send(200, {"ok": True, "block": "", "titles": [], "took_ms": 0.0})
                return
            with LOCK:
                rows = hybrid(query, top_k, include_shared)
            block = format_block(rows, budget)
            titles = [r.get("title") for r in rows][:top_k]
            took = (time.perf_counter() - t0) * 1000.0
            _log_query(query, titles, took, len(block))
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
