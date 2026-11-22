"""Tests for encoder provenance, read-only retrieval and the shared ranker.

No Postgres: the sqlite store exercises the same contract, and the ranker is a pure function.
Run with: PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 <venv>/bin/python -m pytest tests/test_provenance_touch.py -q
"""

from datetime import datetime, timedelta, timezone

import pytest

from gomaa import recall_rank
from gomaa.provenance import normalise_model_id, same_encoder
from gomaa.stores.sqlite import SQLiteStore


# --- provenance -------------------------------------------------------------------------

@pytest.mark.parametrize("tag,expected", [
    ("remote:all-MiniLM-L6-v2", "all-minilm-l6-v2"),
    ("st:all-MiniLM-L6-v2", "all-minilm-l6-v2"),
    ("st:sentence-transformers/all-MiniLM-L6-v2", "all-minilm-l6-v2"),
    ("all-MiniLM-L6-v2", "all-minilm-l6-v2"),
    ("hash-v1", ""),
    (None, ""),
    ("", ""),
])
def test_normalise_model_id(tag, expected):
    assert normalise_model_id(tag) == expected


def test_same_encoder_same_model_different_transport():
    assert same_encoder("st:all-MiniLM-L6-v2", "remote:all-MiniLM-L6-v2")
    assert same_encoder("st:sentence-transformers/all-MiniLM-L6-v2", "remote:all-MiniLM-L6-v2")


def test_same_encoder_rejects_hash_and_unknown():
    assert not same_encoder("hash-v1", "remote:all-MiniLM-L6-v2")
    assert not same_encoder(None, "remote:all-MiniLM-L6-v2")   # unknown is not equality
    assert not same_encoder("remote:bge-m3", "remote:all-MiniLM-L6-v2")


# --- store: visibility + touch ----------------------------------------------------------

def _store(tmp_path):
    store = SQLiteStore(str(tmp_path / "m.db"))
    vec = [1.0] + [0.0] * 383
    for i, eid in enumerate(["st:all-MiniLM-L6-v2", "remote:all-MiniLM-L6-v2", "hash-v1", None]):
        store.upsert_note(
            title=f"note {i}", content=f"body about portal pricing {i}", tags=["test"],
            wing="projects", room="gomaa", embedding=vec, embedder_id=eid,
        )
    return store, vec


def test_same_model_rows_are_visible_across_transport(tmp_path):
    store, vec = _store(tmp_path)
    titles = {r["title"] for r in store.search_semantic(vec, 10, embedder_id="remote:all-MiniLM-L6-v2")}
    assert "note 0" in titles, "st: row must be visible to the remote encoder (same weights)"
    assert "note 1" in titles
    assert "note 3" in titles, "NULL provenance stays visible"
    assert "note 2" not in titles, "hash-v1 is not a model and must stay excluded"


def test_different_model_is_excluded(tmp_path):
    store, vec = _store(tmp_path)
    titles = {r["title"] for r in store.search_semantic(vec, 10, embedder_id="remote:bge-m3")}
    assert titles == {"note 3"}          # only the unknown-provenance row


def test_touch_false_leaves_access_count_untouched(tmp_path):
    store, vec = _store(tmp_path)
    before = sum(r["access_count"] for r in store.search_semantic(vec, 10, touch=False))
    again = sum(r["access_count"] for r in store.search_semantic(vec, 10, touch=False))
    assert before == again, "a read-only sweep must not change access_count"
    store.search_semantic(vec, 10)                     # default touch=True still counts
    assert sum(r["access_count"] for r in store.search_semantic(vec, 10, touch=False)) > before


def test_keyword_touch_false_leaves_access_count_untouched(tmp_path):
    store, vec = _store(tmp_path)
    before = sum(r["access_count"] for r in store.search_keyword("portal pricing", 10, touch=False))
    store.search_keyword("portal pricing", 10, touch=False)
    assert sum(r["access_count"] for r in store.search_keyword("portal pricing", 10, touch=False)) == before


# --- ranking ----------------------------------------------------------------------------

def _row(title, days, tags, room="gomaa", wing="projects", content="body", superseded_by=None):
    return {
        "title": title, "content": content, "tags": tags, "wing": wing, "room": room,
        "created_at": datetime.now(timezone.utc) - timedelta(days=days),
        "superseded_by": superseded_by,
    }


def test_perishable_is_tag_and_shape_not_title_words():
    assert recall_rank.is_perishable(_row("Anything at all", 30, ["live-state"]))
    assert recall_rank.is_perishable(_row("ERP state", 30, [], content="As of 2026-08-01 state at 4.0"))
    assert not recall_rank.is_perishable(_row("Status reporting preference", 30, ["user-preference", "status"]))
    assert not recall_rank.is_perishable(_row("Cron drift knowledge", 30, ["doctrine"]))
    assert not recall_rank.is_perishable(_row("Pharmacy pricing decision", 30, [], content="frozen until EK"))


def test_old_snapshot_is_demoted_below_a_fresh_note():
    rows = recall_rank.rank_rows(
        [_row("Gomaa fleet state 2026-09-01", 80, ["status", "live-state"], content="As of 2026-09-01 state at v3.4.0"),
         _row("Pharmacy portal pricing frozen", 2, [], room="pharmacy-b2b-portal")],
        [], query="what is the current state of gomaa", top_k=2,
    )
    assert rows[0]["title"] == "Pharmacy portal pricing frozen"
    assert rows[1]["_perishable"] is True


def test_perishable_note_is_demoted_not_erased():
    rows = recall_rank.rank_rows([_row("Old snapshot", 50, ["live-state"])], [], query="old snapshot", top_k=4)
    assert [r["title"] for r in rows] == ["Old snapshot"], "a store whose only answer is a snapshot must still answer"


def test_current_state_tag_wins_its_own_question():
    state = _row("Gomaa fleet state 2026-11-22", 0, ["gomaa", "status", "fleet", "current-state"])
    lesson = _row("Gomaa release checklist must write the current-state note", 1, ["gomaa", "state-note", "process"],
                  content="the query 'what is the current state of gomaa' returned old notes")
    rows = recall_rank.rank_rows([lesson], [state], query="what is the current state of gomaa", top_k=2)
    assert rows[0]["title"].startswith("Gomaa fleet state")


def test_superseded_and_probe_rows_are_skipped():
    rows = recall_rank.rank_rows(
        [_row("Replaced", 1, [], superseded_by=9), _row("Probe fixture", 1, ["probe"])],
        [], query="anything", top_k=5,
    )
    assert rows == []


def test_format_block_reports_only_rendered_titles():
    rows = [_row(f"note {i}", 1, []) for i in range(4)]
    block, titles = recall_rank.format_block(rows, budget_chars=120)
    assert titles and len(titles) < 4, "truncated notes must not be reported as injected"
    assert block.count("\n") + 1 == len(titles)


def test_format_block_never_returns_empty_when_rows_exist():
    block, titles = recall_rank.format_block([_row("only note", 1, [])], budget_chars=10)
    assert block and titles == ["only note"]
