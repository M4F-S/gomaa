import os
import tempfile
import pytest
from gomaa.consolidation import ConsolidationEngine
from gomaa.core import UnifiedMemorySystem
from gomaa.stores.sqlite import SQLiteStore
from gomaa.vault import VaultManager
from gomaa.embedder import Embedder


class TestConsolidation:
    def test_consolidation_engine_on_sqlite(self, tmp_path):
        db_path = str(tmp_path / "consolidation_test.db")
        store = SQLiteStore(db_path)
        vault = VaultManager(str(tmp_path / "vault"))
        embedder = Embedder()

        engine = ConsolidationEngine(db=store, vault=vault, embedder=embedder)
        stats = engine.run(decay_factor=0.95, archive_threshold=0.10)

        assert "archived" in stats
        assert "relinked" in stats
        assert isinstance(stats["archived"], int)
        assert isinstance(stats["relinked"], int)

    def test_unified_memory_consolidate_sqlite(self, tmp_path):
        db_path = f"sqlite://{tmp_path / 'unified_test.db'}"
        vault_path = str(tmp_path / "vault")
        mem = UnifiedMemorySystem(vault_path=vault_path, dsn=db_path, auto_sync=False)

        # Store an active note and an old note
        mem.remember("Current Architecture", "Details about system design.", tags=["arch"], salience=0.8)
        mem.remember("Temporary Log", "Old debug logs.", tags=["temp"], salience=0.04)

        res = mem.consolidate(decay_rate=0.95, archive_threshold=0.05)
        assert "reconciled_links" in res
        assert "decayed" in res
        assert "archived" in res
        assert "engine" in res
        assert isinstance(res["engine"], dict)
