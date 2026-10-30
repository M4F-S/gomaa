"""Graph search must honour scope: walking links crosses wings by design.

Note: this store's search_graph returns neighbouring notes, not the seed itself
(the seed is excluded by `row["id"] != root["id"]`), so a correctly scoped walk
that has no in-scope neighbours legitimately returns [].
"""
import pytest

from gomaa.core import UnifiedMemorySystem

BODY = "A memory body long enough to pass the admission controller."


@pytest.fixture
def store(tmp_path):
    m = UnifiedMemorySystem(vault_path=str(tmp_path / "vault"), dsn=str(tmp_path / "g.db"))
    vp = str(tmp_path / "vault")
    a = m.db.upsert_note("Alpha Hub", BODY, [], wing="alpha", room="r1", vault_path=vp)
    b = m.db.upsert_note("Beta Leaf", BODY, [], wing="beta", room="r1", vault_path=vp)
    m.db.update_links(a, ["Beta Leaf"])
    return m.db, a, b


def test_graph_ignores_out_of_scope_neighbour(store):
    db, a, b = store

    unscoped = db.search_graph("Alpha Hub")
    assert "Beta Leaf" in {r["title"] for r in unscoped}, \
        "control: the cross-wing link must exist, otherwise this test proves nothing"

    scoped = db.search_graph("Alpha Hub", scope={"wing": "alpha"})
    assert all(r["wing"] == "alpha" for r in scoped), \
        f"scope leaked: {[(r['title'], r['wing']) for r in scoped]}"


def test_graph_scope_can_be_empty(store):
    db, a, b = store
    assert db.search_graph("Alpha Hub", scope={"wing": "gamma"}) == []
