"""Unit tests for the read-only recall service (no Postgres, no model download)."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer

import pytest

from gomaa.recall_service import (
    RecallService,
    build_handler,
    format_block,
    rank_rows,
)


def _row(title, wing="projects", room="demo", content="body", score=0.5, created=None):
    return {"title": title, "wing": wing, "room": room, "content": content,
            "score": score, "created_at": created}


# -- ranking -----------------------------------------------------------------

def test_rrf_prefers_rows_found_by_both_retrievers():
    both = _row("Found twice")
    sem_only = _row("Semantic only")
    kw_only = _row("Keyword only")
    rows = rank_rows([both, sem_only], [both, kw_only], query="anything", top_k=3)
    assert rows[0]["title"] == "Found twice"
    assert {r["title"] for r in rows[1:]} == {"Semantic only", "Keyword only"}


def test_generic_room_note_loses_to_specific_project_note():
    generic = _row("Fleet wide policy", wing="fleet", room="general")
    specific = _row("Pharmacy portal scope locked", wing="projects", room="pharmacy-b2b-portal")
    rows = rank_rows([generic, specific], [], query="what did we lock down about the portal", top_k=2)
    assert rows[0]["title"] == "Pharmacy portal scope locked"


def test_preference_question_keeps_preference_notes():
    preference = _row("Preferred agent name is Old", wing="operations", room="user-preferences")
    unrelated = _row("Model roster", wing="operations", room="agent-config")
    rows = rank_rows([preference, unrelated], [],
                     query="how should you address me, what do you prefer", top_k=2)
    assert rows[0]["title"] == "Preferred agent name is Old"


def test_room_named_in_query_is_boosted():
    on_topic = _row("Build pipeline", wing="projects", room="gomaa")
    off_topic = _row("Build pipeline retro", wing="projects", room="design")
    rows = rank_rows([on_topic, off_topic], [], query="what is the state of gomaa", top_k=2)
    assert rows[0]["room"] == "gomaa"


def test_shared_rows_are_penalised_and_do_not_duplicate():
    shared = _row("Gomaa v4 verification", wing="shared", room="diagnostics")
    local = _row("Gomaa v5 plan", wing="projects", room="gomaa")
    rows = rank_rows([local], [], [shared, local], query="gomaa", top_k=5)
    titles = [r["title"] for r in rows]
    assert titles.count("Gomaa v4 verification") == 1
    assert titles.count("Gomaa v5 plan") == 1
    assert rows[0]["title"] == "Gomaa v5 plan"


def test_top_k_is_respected():
    rows = rank_rows([_row(f"note {i}") for i in range(10)], [], query="note", top_k=3)
    assert len(rows) == 3


def test_recency_is_only_a_tiebreak():
    old = _row("Same title A", created=datetime(2020, 1, 1, tzinfo=timezone.utc))
    new = _row("Same title B", created=datetime.now(timezone.utc))
    # A is first in both retrievers, B only trails in one: rank overlap must dominate recency.
    rows = rank_rows([old, new], [old], query="same title", top_k=2, now=datetime.now(timezone.utc))
    assert rows[0]["title"] == "Same title A"
    assert len(rows) == 2  # both rows survive, recency did not delete anything


# -- formatting --------------------------------------------------------------

def test_format_block_honours_budget():
    rows = [_row(f"note {i}", content="x" * 500) for i in range(5)]
    block = format_block(rows, budget_chars=200)
    assert block                       # a budget below one bullet still returns its start
    assert len(block) <= 200


def test_format_block_truncates_long_content():
    block = format_block([_row("t", content="y" * 1000)], budget_chars=5000)
    assert "…" in block


# -- service -----------------------------------------------------------------

class _FakeDB:
    def __init__(self, semantic, keyword):
        self._semantic, self._keyword = semantic, keyword
        self.writes = 0

    def search_semantic(self, *args, **kwargs):
        return list(self._semantic)

    def search_keyword(self, *args, **kwargs):
        return list(self._keyword)

    def count_notes(self):
        return 42


class _FakeEmbedder:
    embedder_id = "test-encoder"

    def embed_query(self, query):
        return [0.1, 0.2, 0.3]


class _FakeMemory:
    def __init__(self, semantic, keyword):
        self.db = _FakeDB(semantic, keyword)
        self.embedder = _FakeEmbedder()
        self.shared_db = None


def test_service_returns_block_and_titles_without_writing():
    memory = _FakeMemory([_row("Pharmacy portal scope locked")], [])
    service = RecallService(memory, top_k=2, budget_chars=500)
    result = service.recall("what did we lock down about the pharmacy portal")
    assert result["ok"] is True
    assert "Pharmacy portal scope locked" in result["block"]
    assert result["titles"] == ["Pharmacy portal scope locked"]
    assert memory.db.writes == 0


def test_service_shared_off_by_default_and_skips_short_queries():
    memory = _FakeMemory([_row("anything")], [])
    service = RecallService(memory, top_k=2)
    assert service.recall("")["block"] == ""
    assert service.recall("hi")["block"] == ""       # < 3 chars: no store call
    assert service.recall("anything at all")["ok"] is True


def test_http_handler_serves_health_and_recall():
    memory = _FakeMemory([_row("Deploy runbook", content="steps")], [])
    service = RecallService(memory, top_k=1, budget_chars=300)
    server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(service))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with urllib.request.urlopen(base + "/health", timeout=5) as response:
            assert json.loads(response.read())["notes"] == 42

        request = urllib.request.Request(
            base + "/recall",
            data=json.dumps({"query": "deploy runbook", "top_k": 1}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read())
        assert payload["titles"] == ["Deploy runbook"]

        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(base + "/nope", timeout=5)
    finally:
        server.shutdown()
        server.server_close()


def test_superseded_notes_are_never_returned():
    old = dict(_row("Belya live state 2026-11-01"), superseded_by="newer-note-id")
    new = _row("Belya Phase 1d deployed")
    rows = rank_rows([old, new], [new], query="belya status", top_k=2)
    assert [r["title"] for r in rows] == ["Belya Phase 1d deployed"]


def test_old_perishable_snapshot_loses_to_fresh_note():
    now = datetime(2026, 11, 20, tzinfo=timezone.utc)
    stale = dict(_row("Belya live state 2026-11-01", created=datetime(2026, 11, 1, tzinfo=timezone.utc)),
                 tags=["belya", "live-state"])
    fresh = _row("Belya Phase 1d deployed", created=datetime(2026, 11, 19, tzinfo=timezone.utc))
    rows = rank_rows([stale, fresh], [stale, fresh], query="what is belya status", top_k=2, now=now)
    assert rows[0]["title"] == "Belya Phase 1d deployed"


def test_perishable_note_carries_as_of_label():
    now = datetime(2026, 11, 20, tzinfo=timezone.utc)
    stale = dict(_row("Belya live state 2026-11-01", created=datetime(2026, 11, 1, tzinfo=timezone.utc)),
                 tags=["live-state"])
    block = format_block(rank_rows([stale], [stale], query="belya", top_k=1, now=now))
    assert "[as of 2026-11-01]" in block
