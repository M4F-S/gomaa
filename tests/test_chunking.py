import pytest
import tempfile
import os
from mnemosyne.core import UnifiedMemorySystem


class TestChunking:
    def test_large_turn_sliding_window(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "chunk.db")
            mem = UnifiedMemorySystem(vault_path=tmpdir, dsn=db_path)

            # Generate large 3,500-character transcript turn
            large_code = "User: How to configure Docker?\nAssistant:\n```python\n" + ("x = 42\n" * 400) + "```"
            res = mem.ingest_session(large_code, wing="devops", room="docker")

            assert res["success"] is True
            assert res["units_ingested"] >= 3  # Sub-chunks created

            # Verify the chunked turn content is searchable and titles have Part
            results = mem.recall("x = 42", mode="keyword")
            assert len(results) >= 1
            assert any("Part" in r["title"] for r in results)
