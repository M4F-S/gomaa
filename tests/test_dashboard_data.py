"""Issues #4 and #5: the dashboard must read, not search.

search_keyword caps at top_k and bumps access_count on every call, so using it
as a listing API under-reported totals and made each dashboard refresh look like
retrieval — corrupting the popularity signal that ranking and decay read.
"""
import pytest

from gomaa.stores.sqlite import SQLiteStore

BODY = "A memory body long enough to pass the admission controller."


@pytest.fixture
def store(tmp_path):
    return SQLiteStore(str(tmp_path / "g.db"))


def _fill(store, n=250):
    for i in range(n):
        store.upsert_note(f"Note {i:04d}", BODY, [], wing="bulk", room="r1",
                          vault_path="/v", embedding=[0.01] * 384)


def test_count_is_not_capped_at_the_old_top_n(store):
    _fill(store, 250)
    assert store.count_notes() == 250, "count_notes must not be a top-N sample"


def test_listing_paginates_and_reports_created_at(store):
    _fill(store, 250)
    page = store.list_notes(limit=150)
    assert len(page) == 150
    assert all(row.get("created_at") for row in page), "created_at missing (issue #4)"
    assert len(store.list_notes(limit=100, offset=200)) == 50


def test_pinned_is_derived_from_the_tag(store):
    store.upsert_note("Pinned note", BODY, ["pinned"], wing="qa", room="r",
                      vault_path="/v", embedding=[0.01] * 384)
    store.upsert_note("Plain note", BODY, [], wing="qa", room="r",
                      vault_path="/v", embedding=[0.01] * 384)
    rows = {r["title"]: r for r in store.list_notes(limit=10)}
    assert rows["Pinned note"]["pinned"] is True
    assert rows["Plain note"]["pinned"] is False


def test_listing_does_not_touch_access_count(store):
    _fill(store, 5)

    def snapshot():
        with store._conn() as c:
            return {r["id"]: r["access_count"] for r in
                    c.execute("SELECT id, access_count FROM notes").fetchall()}

    before = snapshot()
    store.list_notes(limit=100)
    store.count_notes()
    store.count_by_wing_room()
    after = snapshot()
    assert before == after, "a read path modified access_count (issue #5)"


def test_same_title_in_two_scopes_is_listed_twice(store):
    store.upsert_note("Shared", BODY, [], wing="alpha", room="r1",
                      vault_path="/v", embedding=[0.01] * 384)
    store.upsert_note("Shared", BODY, [], wing="beta", room="r1",
                      vault_path="/v", embedding=[0.01] * 384)
    rows = [r for r in store.list_notes(limit=10) if r["title"] == "Shared"]
    assert len(rows) == 2, f"listing collapsed scopes: {[(r['wing'], r['room']) for r in rows]}"


def test_count_by_wing_room_matches_the_total(store):
    _fill(store, 20)
    store.upsert_note("Other", BODY, [], wing="misc", room="r9",
                      vault_path="/v", embedding=[0.01] * 384)
    buckets = store.count_by_wing_room()
    assert sum(b["count"] for b in buckets) == store.count_notes() == 21
