import pytest
import tempfile
import os
from gomaa.stores.sqlite import SQLiteStore


class TestSQLiteStore:
    @pytest.fixture
    def store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            yield SQLiteStore(db_path)

    def test_upsert_and_search(self, store):
        note_id = store.upsert_note(
            title="Architecture Overview",
            content="Details about the system architecture and pgvector design.",
            tags=["architecture", "system"],
            note_type="concept",
            status="active",
            salience=0.8,
            embedding=[0.1] * 384,
            vault_path="/tmp/vault",
            wing="engineering",
            room="architecture",
        )
        assert note_id is not None

        # Search with scope
        results = store.search_keyword("architecture", top_k=5, scope={"wing": "engineering"})
        assert len(results) == 1
        assert results[0]["title"] == "Architecture Overview"
        assert results[0]["wing"] == "engineering"

        # Search with mismatch scope
        results_mismatch = store.search_keyword("architecture", top_k=5, scope={"wing": "marketing"})
        assert len(results_mismatch) == 0

    def test_semantic_search(self, store):
        store.upsert_note(
            title="Machine Learning",
            content="Neural networks and transformers.",
            tags=["ai"],
            note_type="concept",
            status="active",
            salience=0.5,
            embedding=[0.5] * 384,
            vault_path="/tmp/vault",
            wing="ai",
            room="models",
        )
        results = store.search_semantic([0.5] * 384, top_k=5, scope={"wing": "ai"})
        assert len(results) == 1
        assert results[0]["score"] > 0.99

    def test_delete_note(self, store):
        store.upsert_note(
            title="To Delete",
            content="Temporary content",
            tags=[],
            note_type="concept",
            status="active",
            salience=0.5,
            embedding=[0.1] * 384,
            vault_path="/tmp/vault",
        )
        assert store.delete_note("To Delete", "/tmp/vault") is True
        results = store.search_keyword("Temporary")
        assert len(results) == 0

    def test_timeline_and_history(self, store):
        store.log_timeline("remember", note_title="Test Note", summary="Created test note")
        timeline = store.get_timeline(limit=10)
        assert len(timeline) == 1
        assert timeline[0]["title"] == "Test Note"
        assert timeline[0]["operation"] == "remember"

        # Update note to test version archiving
        store.upsert_note("Versioned", "v1 content", [], "concept", "active", 0.5, [0.1] * 384, "/tmp/vault")
        store.upsert_note("Versioned", "v2 content", [], "concept", "active", 0.7, [0.1] * 384, "/tmp/vault")
        history = store.get_note_history("Versioned", limit=5)
        assert len(history) >= 1
        assert "v1 content" in history[0]["preview"]

    def test_decay_with_pinned_immunity(self, store):
        # Normal note
        store.upsert_note("Decaying", "old content", [], "concept", "active", 0.04, [0.1] * 384, "/tmp/vault")
        # Pinned note
        store.upsert_note("Permanent", "core secret", ["pinned"], "concept", "active", 0.04, [0.1] * 384, "/tmp/vault")

        # Set last_accessed_at to 10 days ago manually
        with store._conn() as conn:
            conn.execute("UPDATE notes SET last_accessed_at = datetime('now', '-10 days');")
            conn.commit()

        res = store.apply_decay(decay_rate=0.95, archive_threshold=0.05)
        assert res["archived"] == 1  # only Decaying note archived

        stats = store.get_stats()
        assert stats["notes"] == 1  # Permanent note remains active
        assert stats["archived"] == 1
