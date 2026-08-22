import pytest
import tempfile
import os
from mnemosyne.stores.sqlite import SQLiteStore


class TestSQLiteStore:
    @pytest.fixture
    def store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            yield SQLiteStore(db_path)

    def test_upsert_and_search(self, store):
        store.upsert_note(
            "Test Note", "test content", ["tag"], "concept", "active", 0.5,
            [0.1] * 384, "/tmp/vault"
        )
        results = store.search_keyword("test", top_k=5)
        assert len(results) > 0
        assert results[0]["title"] == "Test Note"

    def test_semantic_search(self, store):
        store.upsert_note(
            "Note A", "machine learning", [], "concept", "active", 0.5,
            [0.1] * 384, "/tmp/vault"
        )
        store.upsert_note(
            "Note B", "deep learning", [], "concept", "active", 0.5,
            [0.2] * 384, "/tmp/vault"
        )
        results = store.search_semantic([0.15] * 384, top_k=2)
        assert len(results) == 2

    def test_delete_note(self, store):
        store.upsert_note(
            "Delete Me", "content", [], "concept", "active", 0.5,
            [0.1] * 384, "/tmp/vault"
        )
        assert store.delete_note("Delete Me", "/tmp/vault")
        assert not store.delete_note("Delete Me", "/tmp/vault")

    def test_hybrid_search(self, store):
        store.upsert_note(
            "Note A", "machine learning", [], "concept", "active", 0.5,
            [0.1] * 384, "/tmp/vault"
        )
        results = store.hybrid_search("machine", [0.1] * 384, top_k=5)
        assert len(results) > 0

    def test_graph_search(self, store):
        id1 = store.upsert_note(
            "Source", "content", [], "concept", "active", 0.5,
            [0.1] * 384, "/tmp/vault"
        )
        store.upsert_note(
            "Target", "content", [], "concept", "active", 0.5,
            [0.1] * 384, "/tmp/vault"
        )
        store.update_links(id1, ["Target"])
        results = store.search_graph("Source", depth=2, top_k=5)
        assert len(results) > 0
