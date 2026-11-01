"""Postgres-only regressions.

The default suite runs on SQLite, so Postgres-specific SQL (vector casts,
savepoints, ON CONFLICT semantics) is otherwise untested — which is how a
`COALESCE(%s, embedding)` type error shipped. These run only when
MEMORY_TEST_DSN points at a throwaway database:

    MEMORY_TEST_DSN=postgresql://... pytest tests/test_postgres_contract.py
"""
import os

import pytest

psycopg2 = pytest.importorskip("psycopg2")
DSN = os.environ.get("MEMORY_TEST_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="MEMORY_TEST_DSN not set (Postgres contract tests)")

VP = "/tmp/pg-contract"
E1 = [0.01] * 384
E2 = [0.02] * 384
BODY1 = "First body, long enough to pass the admission controller."
BODY2 = "Second body, revised, long enough to pass admission control."


@pytest.fixture
def store():
    from gomaa.stores.postgres import PgVectorStore

    s = PgVectorStore(DSN)
    yield s
    for title, wing, room in (("PG Update Probe", "qa", "pg"),
                              ("PG Scope Probe", "alpha", "pg"),
                              ("PG Scope Probe", "beta", "pg"),
                              ("PG Tag Probe", "qa", "tag")):
        try:
            s.delete_note(title, wing=wing, room=room)
        except Exception:
            pass


def test_update_existing_note_with_a_new_embedding(store):
    """Regression: COALESCE(%s, embedding) cannot unify numeric[] with vector."""
    a = store.upsert_note("PG Update Probe", BODY1, [], wing="qa", room="pg",
                          vault_path=VP, embedding=E1)
    b = store.upsert_note("PG Update Probe", BODY2, [], wing="qa", room="pg",
                          vault_path=VP, embedding=E2)
    assert a == b, "update must reuse the row, not create a second one"
    rows = store.search_keyword("PG Update Probe", top_k=5, scope={"wing": "qa", "room": "pg"})
    assert rows and "Second body" in rows[0]["content"], "content was not updated"


def test_same_title_in_two_scopes_coexists(store):
    store.upsert_note("PG Scope Probe", BODY1, [], wing="alpha", room="pg",
                      vault_path=VP, embedding=E1)
    store.upsert_note("PG Scope Probe", BODY2, [], wing="beta", room="pg",
                      vault_path=VP, embedding=E1)
    rows = store.search_keyword("PG Scope Probe", top_k=10)
    assert len([r for r in rows if r["title"] == "PG Scope Probe"]) == 2


def test_hash_tagged_rows_are_excluded_from_semantic_ranking(store):
    store.upsert_note("PG Tag Probe", BODY1, [], wing="qa", room="tag",
                      vault_path=VP, embedding=E1, embedder_id="st:test")
    store.upsert_note("PG Tag Probe", BODY2, [], wing="qa", room="tag2",
                      vault_path=VP, embedding=E1, embedder_id="hash-v1")
    try:
        hits = store.search_semantic(E1, top_k=20, embedder_id="st:test")
        tags = {r["title"] for r in hits if r["title"].startswith("PG Tag Probe")}
        assert "PG Tag Probe" in tags or tags, "real row must be searchable"
        wings = {r["room"] for r in hits if r["title"] == "PG Tag Probe"}
        assert "tag2" not in wings, "hash-tagged row leaked into semantic results"
    finally:
        store.delete_note("PG Tag Probe", wing="qa", room="tag2")


def test_scope_is_enforced_in_graph_search(store):
    a = store.upsert_note("PG Scope Probe", BODY1, [], wing="alpha", room="pg",
                          vault_path=VP, embedding=E1)
    store.upsert_note("PG Scope Probe", BODY2, [], wing="beta", room="pg",
                      vault_path=VP, embedding=E1)
    store.update_links(a, ["PG Scope Probe"])
    scoped = store.search_graph("PG Scope Probe", scope={"wing": "alpha"})
    assert all(r["wing"] == "alpha" for r in scoped), \
        f"scope leaked: {[(r['title'], r['wing']) for r in scoped]}"


def test_reembedding_retags_the_row(store):
    """A note first written by the hash fallback must become searchable once it
    is re-embedded by the real model — the UPDATE must rewrite embedder_id."""
    store.upsert_note("PG Tag Probe", BODY1, [], wing="qa", room="tag",
                      vault_path=VP, embedding=E1, embedder_id="hash-v1")
    store.upsert_note("PG Tag Probe", BODY2, [], wing="qa", room="tag",
                      vault_path=VP, embedding=E2, embedder_id="st:test")
    hits = store.search_semantic(E2, top_k=10, embedder_id="st:test")
    assert any(r["title"] == "PG Tag Probe" for r in hits), \
        "row kept hash-v1 after re-embedding and stayed invisible"


def test_upsert_waits_for_a_row_locked_by_another_session(store):
    """Proves FOR UPDATE is in play: a second writer must block, not clobber."""
    import threading
    import time

    store.upsert_note("Lock Probe", BODY1, [], wing="qa", room="lock", vault_path=VP, embedding=E1)
    conn = psycopg2.connect(DSN)
    conn.autocommit = False
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM notes WHERE title=%s AND wing=%s AND room=%s FOR UPDATE",
        ("Lock Probe", "qa", "lock"),
    )
    started = time.time()
    err = []

    def writer():
        try:
            store.upsert_note("Lock Probe", BODY2, [], wing="qa", room="lock",
                              vault_path=VP, embedding=E2)
        except Exception as e:  # surfaced below
            err.append(e)

    th = threading.Thread(target=writer, daemon=True)
    th.start()
    time.sleep(0.6)          # writer must still be blocked here
    blocked = th.is_alive()
    conn.commit()            # release
    conn.close()
    th.join(timeout=10)
    elapsed = time.time() - started

    assert not err, f"writer failed: {err}"
    assert blocked and elapsed >= 0.5, f"writer did not block (elapsed {elapsed:.2f}s)"
    rows = store.search_keyword("Lock Probe", top_k=5, scope={"wing": "qa", "room": "lock"})
    assert rows and "Second body" in rows[0]["content"], "write after the lock was lost"


def test_ppr_respects_scope(store):
    a = store.upsert_note("PPR Alpha", BODY1, [], wing="alpha", room="ppr",
                          vault_path=VP, embedding=E1)
    store.upsert_note("PPR Beta", BODY2, [], wing="beta", room="ppr",
                      vault_path=VP, embedding=E1)
    store.update_links(a, ["PPR Beta"])
    try:
        scoped = store.search_associative_ppr(E1, top_k=10, scope={"wing": "alpha"})
        assert all(r["wing"] == "alpha" for r in scoped), \
            f"PPR leaked: {[(r['title'], r['wing']) for r in scoped]}"
    finally:
        store.delete_note("PPR Beta", wing="beta", room="ppr")


def test_missing_scope_key_is_added_for_an_unrecognised_legacy_constraint():
    """A 4.0.0 table whose unique constraint has an unexpected name must still
    get the scope key; the migration used to skip silently in that case."""
    import re
    import uuid

    src = open("gomaa/stores/postgres.py").read()
    block = re.search(r"(DO \$\$.*?END \$\$;)", src, re.S).group(1)

    schema = "probe_" + uuid.uuid4().hex[:8]
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    cur = conn.cursor()
    try:
        cur.execute(f"CREATE SCHEMA {schema}")
        cur.execute(
            f"CREATE TABLE {schema}.notes (id serial primary key, title text, wing text, "
            f"room text, vault_path text, CONSTRAINT legacy_odd_name UNIQUE (title, vault_path))"
        )
        cur.execute(f"SET search_path TO {schema}")
        cur.execute(block)
        cur.execute(
            "select conname from pg_constraint where conrelid=%s::regclass and contype='u'",
            (f"{schema}.notes",),
        )
        names = [r[0] for r in cur.fetchall()]
        assert "notes_scope_title_unique" in names, f"scope key not added: {names}"
    finally:
        cur.execute("SET search_path TO public")
        cur.execute(f"DROP SCHEMA {schema} CASCADE")
        conn.close()
