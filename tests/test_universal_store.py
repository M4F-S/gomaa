"""Store-contract tests: both backends must honour the same guarantees.

Gomaa is a universal memory layer — any agent, either backend — so a fix that
works only on Postgres (or only for this deployment) is a bug.
"""
import sqlite3

import pytest

from gomaa.core import UnifiedMemorySystem
from gomaa.stores.sqlite import SQLiteStore

BODY = "A memory body long enough to pass the admission controller."
VEC = [0.01] * 384


def test_sqlite_search_excludes_other_encoder(tmp_path):
    store = SQLiteStore(str(tmp_path / "g.db"))
    store.upsert_note("Real", BODY, [], wing="w", room="r", embedding=VEC,
                      embedder_id="st:model-a")
    store.upsert_note("Noise", BODY, [], wing="w", room="r", embedding=VEC,
                      embedder_id="hash-v1")

    unfiltered = {r["title"] for r in store.search_semantic(VEC, top_k=10)}
    filtered = {r["title"] for r in store.search_semantic(VEC, top_k=10, embedder_id="st:model-a")}

    assert {"Real", "Noise"} <= unfiltered, "control: both rows must be searchable"
    assert "Real" in filtered
    assert "Noise" not in filtered


def test_sqlite_keeps_untagged_rows_visible(tmp_path):
    store = SQLiteStore(str(tmp_path / "g.db"))
    store.upsert_note("Legacy", BODY, [], wing="w", room="r", embedding=VEC)

    hits = {r["title"] for r in store.search_semantic(VEC, top_k=10, embedder_id="st:model-a")}
    assert "Legacy" in hits, "rows written before tagging must not disappear"


def test_sqlite_adds_embedder_column_to_a_pre_tag_store(tmp_path):
    path = str(tmp_path / "old.db")
    raw = sqlite3.connect(path)
    raw.execute(
        """CREATE TABLE notes (
            id TEXT PRIMARY KEY, title TEXT, content TEXT, tags TEXT, note_type TEXT,
            status TEXT, salience REAL, embedding TEXT, vault_path TEXT, wing TEXT,
            room TEXT, origin_agent TEXT, memory_type TEXT, episodic_parent_hash TEXT,
            superseded_by TEXT, access_count INTEGER, confidence REAL,
            last_accessed_at TEXT, created_at TEXT, updated_at TEXT,
            UNIQUE(wing, room, title))"""
    )
    raw.commit()
    raw.close()

    store = SQLiteStore(path)  # must migrate in place, not crash
    with store._conn() as c:
        cols = {r[1] for r in c.execute("PRAGMA table_info(notes)").fetchall()}
    assert "embedder_id" in cols


def test_shared_store_graph_respects_scope(tmp_path):
    shared = str(tmp_path / "shared.db")
    mem = UnifiedMemorySystem(
        vault_path=str(tmp_path / "vault"),
        dsn=str(tmp_path / "private.db"),
        shared_dsn=shared,
    )
    store = mem.shared_db
    a = store.upsert_note("Shared Alpha", BODY, [], wing="alpha", room="r1",
                          vault_path=str(tmp_path / "vault"))
    store.upsert_note("Shared Beta", BODY, [], wing="beta", room="r1",
                      vault_path=str(tmp_path / "vault"))
    store.update_links(a, ["Shared Beta"])

    unscoped = store.search_graph("Shared Alpha")
    assert "Shared Beta" in {r["title"] for r in unscoped}, "control: link must exist"

    scoped = store.search_graph("Shared Alpha", scope={"wing": "alpha"})
    assert all(r["wing"] == "alpha" for r in scoped)
