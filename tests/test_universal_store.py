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


def test_sqlite_rebuilds_a_legacy_identity_key(tmp_path):
    """Critical: a 4.0.0 SQLite file is keyed on (title, vault_path). Opening it
    with the new code must rebuild the table, keep the rows, and stop a
    cross-scope write from overwriting another wing's note."""
    path = str(tmp_path / "legacy.db")
    raw = sqlite3.connect(path)
    raw.execute(
        """CREATE TABLE notes (
            id TEXT PRIMARY KEY, title TEXT, content TEXT, tags TEXT, note_type TEXT,
            status TEXT, salience REAL, embedding TEXT, vault_path TEXT, wing TEXT,
            room TEXT, origin_agent TEXT, memory_type TEXT, episodic_parent_hash TEXT,
            superseded_by TEXT, access_count INTEGER, confidence REAL,
            last_accessed_at TEXT, created_at TEXT, updated_at TEXT,
            UNIQUE(title, vault_path))"""
    )
    raw.execute(
        "INSERT INTO notes (id,title,content,tags,vault_path,wing,room,status,salience,"
        "access_count,confidence) VALUES ('a','Dup','alpha body','[]','/v','alpha','r1',"
        "'active',0.5,0,1.0)"
    )
    raw.commit()
    raw.close()

    store = SQLiteStore(path)
    with store._conn() as c:
        ddl = c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='notes'").fetchone()["sql"]
        assert "UNIQUE(wing, room, title)" in ddl, "legacy key was not migrated"
        assert c.execute("SELECT count(*) c FROM notes").fetchone()["c"] == 1, "row lost in rebuild"

    store.upsert_note("Dup", "beta body long enough for admission control.", [], wing="beta", room="r1",
                      vault_path="/v", embedding=[0.1] * 384)
    rows = store.search_keyword("Dup", top_k=10)
    scopes = sorted((r["wing"], r["room"]) for r in rows if r["title"] == "Dup")
    assert ("alpha", "r1") in scopes and ("beta", "r1") in scopes, f"scopes={scopes}"


def test_sqlite_ppr_respects_scope(tmp_path):
    store = SQLiteStore(str(tmp_path / "g.db"))
    a = store.upsert_note("Alpha Seed", BODY, [], wing="alpha", room="r1",
                          vault_path="/v", embedding=VEC)
    store.upsert_note("Beta Target", BODY, [], wing="beta", room="r1",
                      vault_path="/v", embedding=VEC)
    store.update_links(a, ["Beta Target"])

    scoped = store.search_associative_ppr(VEC, top_k=10, scope={"wing": "alpha"})
    assert all(r["wing"] == "alpha" for r in scoped), \
        f"PPR leaked across wings: {[(r['title'], r['wing']) for r in scoped]}"


def test_sqlite_reembedding_retags_the_row(tmp_path):
    store = SQLiteStore(str(tmp_path / "g.db"))
    store.upsert_note("ReTag", BODY, [], wing="qa", room="rt",
                      vault_path="/v", embedding=VEC, embedder_id="hash-v1")
    store.upsert_note("ReTag", BODY, [], wing="qa", room="rt",
                      vault_path="/v", embedding=VEC, embedder_id="st:test")
    hits = store.search_semantic(VEC, top_k=10, embedder_id="st:test")
    assert any(r["title"] == "ReTag" for r in hits), "tag not rewritten on update"


def test_duplicate_groups_block_the_rebuild_but_do_not_brick_the_store(tmp_path):
    """Refusing to merge is right; raising would break every caller."""
    path = str(tmp_path / "dups.db")
    raw = sqlite3.connect(path)
    raw.execute(
        """CREATE TABLE notes (
            id TEXT PRIMARY KEY, title TEXT, content TEXT, tags TEXT, note_type TEXT,
            status TEXT, salience REAL, embedding TEXT, vault_path TEXT, wing TEXT,
            room TEXT, origin_agent TEXT, memory_type TEXT, episodic_parent_hash TEXT,
            superseded_by TEXT, access_count INTEGER, confidence REAL,
            last_accessed_at TEXT, created_at TEXT, updated_at TEXT,
            UNIQUE(title, vault_path))"""
    )
    for i, vp in enumerate(("/v1", "/v2")):
        raw.execute(
            "INSERT INTO notes (id,title,content,tags,vault_path,wing,room,status,"
            "access_count,confidence) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (f"r{i}", "Same", "body", "[]", vp, "alpha", "r1", "active", 0, 1.0),
        )
    raw.commit()
    raw.close()

    store = SQLiteStore(path)  # must not raise
    with store._conn() as c:
        assert c.execute("SELECT count(*) c FROM notes").fetchone()["c"] == 2, "rows lost"
        ddl = c.execute("SELECT sql FROM sqlite_master WHERE name='notes'").fetchone()["sql"]
        assert "UNIQUE(title, vault_path)" in ddl, "merged without a decision"
