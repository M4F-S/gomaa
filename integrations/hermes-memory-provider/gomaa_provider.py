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

Guards that matter in practice (each measured on the live fleet):
  * a turn whose text is host-generated (`[IMPORTANT: Background process…`, `[System note: …]`) is
    not a question about the user's history — querying it injects unrelated notes forever;
  * cron / subagent / flush sessions get a fresh provider per run, so recall there costs a query and
    returns notes with no conversation to use them in; only the primary context recalls;
  * dedupe must compare against the titles **actually rendered** after truncation, or a cut note is
    remembered as delivered and can never be injected again in that session.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional, Set

from agent.memory_provider import MemoryProvider, RecallStatus, spawn_context_thread

logger = logging.getLogger(__name__)

DEFAULT_URL = "http://127.0.0.1:8790"
TOP_K = 3
BUDGET_CHARS = 700
CACHE_TTL_S = 900.0
LIVE_TIMEOUT = (0.3, 2.5)    # blocking prefetch: the turn waits
BACKGROUND_TIMEOUT = (0.3, 5.0)   # queue_prefetch: nobody is waiting
MAX_BLOCK_CHARS = 1200
# Host-generated turn text: a process notice or a system note is not a question.
HOST_TEXT_PREFIXES = ("[important:", "[system note:", "[system:")


def _config() -> Dict[str, Any]:
    try:
        from hermes_cli.config import load_config
        section = (load_config() or {}).get("memory", {}) or {}
        block = section.get("gomaa") or {}
        return dict(block) if isinstance(block, dict) else {}
    except Exception:
        return {}


def _is_host_text(text: str) -> bool:
    return (text or "").lstrip().lower().startswith(HOST_TEXT_PREFIXES)


# A continuation is a turn that adds no topic. Recalling on it guesses a subject and injects
# unrelated history; the conversation itself already carries what "proceed" refers to.
CONTINUATIONS = {
    "proceed", "continue", "go", "go on", "next", "ok", "okay", "yes", "yeah", "yep",
    "do it", "resume", "elaborate", "explain", "more", "and", "so", "what now",
    "what should we do now", "fix it", "why", "how",
}


def _is_continuation(text: str) -> bool:
    t = " ".join((text or "").lower().strip().split())
    t = re.sub(r"^(please|pls|just|now)\s+", "", t)
    if not t:
        return True
    if t in CONTINUATIONS:
        return True
    words = t.split()
    return len(words) <= 2 and words[0] in {"proceed", "continue", "go", "next", "ok", "yes", "resume", "elaborate", "explain"}


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
        self._agent_context = "primary"
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
        # "primary" | "subagent" | "cron" | "flush". Default to primary: an absent kwarg must
        # never silence memory, it must only fail to narrow it.
        self._agent_context = str(kwargs.get("agent_context") or "primary")

    def system_prompt_block(self) -> str:
        """Empty on purpose: MEMORY.md / USER.md are still injected by the built-in provider."""
        return ""

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """None: the obsidian_memory MCP server already publishes the memory_* tools."""
        return []

    # -- retrieval ---------------------------------------------------------

    def _skip(self, query: str) -> bool:
        if not query or not query.strip():
            return True
        if self._agent_context != "primary":
            return True
        if _is_host_text(query):
            return True
        return _is_continuation(query)

    def _call(self, query: str, client=None, timeout=LIVE_TIMEOUT) -> Optional[Dict[str, Any]]:
        import requests
        try:
            r = (client or requests).post(
                f"{self._url}/recall",
                json={"query": query[:500], "top_k": self._top_k,
                      "budget_chars": self._budget, "client": f"provider:{self._agent_context}"},
                timeout=timeout,
            )
            if r.status_code == 200:
                return r.json()
        except Exception as exc:
            logger.debug("gomaa recall service call failed: %s", exc)
        return None

    def queue_prefetch(self, query: str, *, session_id: str = "") -> None:
        """Background query after the turn; `prefetch()` consumes it on the next one."""
        sid = session_id or self._session_id
        if self._skip(query):
            return
        provider = self

        def _run() -> None:
            res = provider._call(query, timeout=BACKGROUND_TIMEOUT)
            if res is not None:
                provider._cache[sid] = {"query": query, "block": res.get("block") or "",
                                        "titles": res.get("titles") or [], "ts": time.time()}

        thread = spawn_context_thread(_run, name="gomaa-queue-prefetch")
        thread.start()

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        sid = session_id or self._session_id
        if self._skip(query):
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
                logger.warning("gomaa recall unavailable for this turn (service slow or down)")
                if cached and cached.get("block"):
                    return ""      # never replay a block for a different question
                return ""
            block, titles = res.get("block") or "", list(res.get("titles") or [])
            self._cache[sid] = {"query": query, "block": block, "titles": titles, "ts": time.time()}
        if not block:
            return ""

        already = self._injected.setdefault(sid, set())
        rendered: List[str] = []
        used = 0
        for line, title in zip(block.split("\n"), titles):
            if title in already:
                continue               # already paid for in this session
            add = len(line) + (1 if rendered else 0)
            if used + add > MAX_BLOCK_CHARS:
                break                  # only the titles actually returned count as injected
            rendered.append(line)
            used += add
            already.add(title)
        if not rendered:
            self._last_count = 0
            return ""
        self._last_count = len(rendered)
        return "Relevant stored notes:\n" + "\n".join(rendered)

    def recall_status(self) -> Optional[RecallStatus]:
        if not self._last_count:
            return None
        return RecallStatus(provider_label="Gomaa", count=self._last_count)

    def shutdown(self) -> None:
        self._cache.clear()


def register(ctx) -> None:
    ctx.register_memory_provider(GomaaMemoryProvider())
