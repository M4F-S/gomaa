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
                    "MEMORY_DB_DSN", "postgresql://mnemosyne:mnemosyne@localhost:5432/mnemosyne"
                ),
                auto_sync=False,
            )
            yield mem

    def test_remember_and_recall(self, memory):
        memory.remember("Test Note", "This is test content", tags=["test"])
        results = memory.recall("test content")
        assert len(results) > 0
        assert any(r["title"] == "Test Note" for r in results)

    def test_hybrid_search(self, memory):
        memory.remember("Note A", "Content about machine learning")
        memory.remember("Note B", "Content about deep learning")
        results = memory.recall("machine learning", mode="hybrid")
        assert len(results) >= 1
