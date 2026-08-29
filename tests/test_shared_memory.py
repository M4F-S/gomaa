import pytest
import tempfile
import os
from gomaa.core import UnifiedMemorySystem


class TestSharedMemory:
    @pytest.fixture
    def memory_pair(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            private_db_path = os.path.join(tmpdir, "private.db")
            shared_db_path = os.path.join(tmpdir, "shared.db")

            mem = UnifiedMemorySystem(
                vault_path=tmpdir,
                dsn=private_db_path,
                shared_dsn=shared_db_path,
                agent_name="agent-toy",
            )
            yield mem

    def test_publish_shared_success(self, memory_pair):
        res = memory_pair.publish_shared(
            title="Shared Fleet Policy",
            content="All agents must use port 15432 for internal Postgres.",
            tags=["policy", "networking"],
        )
        assert res["success"] is True

        # Recall should find it from shared store
        results = memory_pair.recall("internal Postgres", mode="keyword")
        assert len(results) >= 1
        assert results[0]["title"] == "Shared Fleet Policy"
        assert results[0]["source_store"] == "shared"

    def test_publish_shared_blocks_sensitive_keys(self, memory_pair):
        res = memory_pair.publish_shared(
            title="Leaked API Key",
            content="Here is the key: sk-abcdefghijklmnopqrstuvwxyz1234567890",
            tags=["leak"],
        )
        assert res["success"] is False
        assert "Security Violation" in res["error"]
