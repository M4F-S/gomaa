"""Gomaa memory provider — per-turn recall through the local recall service.

Why a service and not a direct query: the gateway venv has no psycopg2, no numpy, no
sentence-transformers and no `gomaa`, and installing them there is the kind of change that breaks
on the next Hermes upgrade. `/opt/data/scripts/gomaa_recall_service.py` runs in the memory venv
with the warm model; this plugin only makes HTTP calls (`requests` is present).

Per-turn shape (agent/memory_provider.py contract):
  * `queue_prefetch()` runs the query OFF the turn, after the previous turn;
  * `prefetch()` returns that cached block, and makes at most one bounded live call when the topic
    changed. The host gives prefetch 8 s and blocks the turn, so never rely on that budget.
  * injected blocks are stamped into the user row and replayed every later request, so the block is
    capped (~1k chars) and titles already injected in this session are dropped.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Set

from agent.memory_provider import MemoryProvider, RecallStatus, spawn_context_thread

logger = logging.getLogger(__name__)

DEFAULT_URL = "http://127.0.0.1:8790"
TOP_K = 4
BUDGET_CHARS = 1000
CACHE_TTL_S = 900.0
LIVE_TIMEOUT = (0.3, 2.5)   # (connect, read) — prefetch blocks the turn; Toy measured 0.4-1.4 s
MAX_BLOCK_CHARS = 1200


def _config() -> Dict[str, Any]:
    try:
        from hermes_cli.config import load_config
        section = (load_config() or {}).get("memory", {}) or {}
        block = section.get("gomaa") or {}
        return dict(block) if isinstance(block, dict) else {}
    except Exception:
        return {}


def _tokens(text: str) -> Set[str]:
    return {t for t in "".join(c.lower() if c.isalnum() else " " for c in (text or "")).split()
            if len(t) > 2}


class GomaaMemoryProvider(MemoryProvider):
    def __init__(self) -> None:
        cfg = _config()
        self._url = str(cfg.get("url") or DEFAULT_URL).rstrip("/")
        self._top_k = int(cfg.get("top_k", TOP_K))
        self._budget = int(cfg.get("budget_chars", BUDGET_CHARS))
        self._session_id = ""
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._injected: Dict[str, Set[str]] = {}
        self._last_count = 0
        self._last_label = ""

    # -- lifecycle ---------------------------------------------------------

    @property
    def name(self) -> str:
        return "gomaa"

    def is_available(self) -> bool:
        """Config only — a network probe here would silently disable recall for a whole session."""
        return bool(self._url)

    def unavailable_reason(self) -> str:
        return "memory.gomaa.url is not configured"

    def initialize(self, session_id: str, **kwargs) -> None:
        self._session_id = session_id or ""

    def system_prompt_block(self) -> str:
        """Empty on purpose: MEMORY.md / USER.md are still injected by the built-in provider."""
        return ""

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """None: the obsidian_memory MCP server already publishes the memory_* tools."""
        return []

    # -- retrieval ---------------------------------------------------------

    def _call(self, query: str, client=None) -> Optional[Dict[str, Any]]:
        import requests
        try:
            r = (client or requests).post(
                f"{self._url}/recall",
                json={"query": query[:500], "top_k": self._top_k, "budget_chars": self._budget},
                timeout=LIVE_TIMEOUT,
            )
            if r.status_code == 200:
                return r.json()
        except Exception as exc:
            logger.debug("gomaa recall service call failed: %s", exc)
        return None

    def queue_prefetch(self, query: str, *, session_id: str = "") -> None:
        """Background query after the turn; `prefetch()` consumes it on the next one."""
        sid = session_id or self._session_id
        if not query or not query.strip():
            return
        provider = self

        def _run() -> None:
            res = provider._call(query)
            if res is not None:
                provider._cache[sid] = {"query": query, "block": res.get("block") or "",
                                        "titles": res.get("titles") or [], "ts": time.time()}

        thread = spawn_context_thread(_run, name="gomaa-queue-prefetch")
        thread.start()

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        sid = session_id or self._session_id
        if not query or not query.strip():
            return ""
        cached = self._cache.get(sid)
        block = ""
        titles: List[str] = []
        fresh = cached and (time.time() - cached["ts"]) < CACHE_TTL_S
        if cached and fresh and cached.get("block"):
            overlap = _tokens(query) & _tokens(cached.get("query", ""))
            union = _tokens(query) | _tokens(cached.get("query", ""))
            if union and len(overlap) / len(union) >= 0.30:
                block, titles = cached["block"], list(cached.get("titles") or [])
        if not block:
            res = self._call(query)
            if res is None:
                return ""
            block, titles = res.get("block") or "", list(res.get("titles") or [])
            self._cache[sid] = {"query": query, "block": block, "titles": titles, "ts": time.time()}
        if not block:
            return ""

        already = self._injected.setdefault(sid, set())
        if titles and all(t in already for t in titles):
            self._last_count = 0
            return ""                      # same notes already paid for in this session
        for t in titles:
            already.add(t)

        if len(block) > MAX_BLOCK_CHARS:
            block = block[:MAX_BLOCK_CHARS].rsplit("\n", 1)[0] + "\n[…]"
        self._last_count = len(titles)
        return "Relevant stored notes:\n" + block

    def recall_status(self) -> Optional[RecallStatus]:
        if not self._last_count:
            return None
        return RecallStatus(provider_label="Gomaa", count=self._last_count)

    def shutdown(self) -> None:
        self._cache.clear()


def register(ctx) -> None:
    ctx.register_memory_provider(GomaaMemoryProvider())
