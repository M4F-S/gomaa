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
