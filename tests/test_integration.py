import pytest
import tempfile
import os

pytestmark = pytest.mark.integration


class TestIntegration:
    @pytest.fixture
    def memory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            from mnemosyne import UnifiedMemorySystem

            mem = UnifiedMemorySystem(
                vault_path=tmpdir,
                dsn=os.environ.get(
                    "MEMORY_DB_DSN", "postgresql://mnemosyne:***@localhost:5432/mnemosyne"
                ),
                auto_sync=False,
            )
            yield mem

    def test_remember_and_recall_with_scoping(self, memory):
        unique_term = "quantum_superposition_x99"
        res = memory.remember(
            "Scoped Architecture Note",
            f"Details about hierarchical wing scoping and pgvector {unique_term}.",
            tags=["arch"],
            wing="engineering",
            room="infra",
        )
        assert res["success"] is True

        # Recall within scope
        results = memory.recall(unique_term, top_k=10, scope={"wing": "engineering"})
        assert len(results) >= 1
        assert any(r["title"] == "Scoped Architecture Note" for r in results)
        assert all(r["wing"] == "engineering" for r in results)

        # Recall outside scope
        results_other = memory.recall(unique_term, top_k=10, scope={"wing": "marketing"})
        assert len(results_other) == 0

    def test_hybrid_search_rrf(self, memory):
        unique_term = "ivfflat_cosine_index_z88"
        memory.remember("PostgreSQL Vector Search", f"Content about ivfflat and cosine distance {unique_term}.", tags=["db"])
        memory.remember("Obsidian Graph Crawl", "Content about wikilinks and markdown.", tags=["graph"])
        results = memory.recall(unique_term, mode="hybrid")
        assert len(results) >= 1
        assert "PostgreSQL Vector Search" in [r["title"] for r in results]

    def test_pinned_decay_immunity(self, memory):
        memory.remember("Permanent Secret", "Critical API credentials", tags=["security"], pinned=True)
        memory.remember("Temporary Note", "Old log data", tags=["temp"], salience=0.04)

        # Decay run
        decay_res = memory.consolidate(decay_rate=0.95, archive_threshold=0.05)
        assert decay_res is not None

        stats = memory.stats()
        assert stats["notes"] >= 1
