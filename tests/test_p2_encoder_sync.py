"""P2: encoder provenance under outage, and sync must embed what it indexes."""
import os
import tempfile

import pytest

from gomaa.core import UnifiedMemorySystem
from gomaa.embedder import Embedder


def test_hash_fallback_reports_itself_when_the_remote_is_dead(monkeypatch):
    """The tag must describe the encoder actually used, not the configured one."""
    monkeypatch.setenv("MEMORY_EMBED_URL", "http://127.0.0.1:9/embed")  # closed port
    e = Embedder(model_name="all-MiniLM-L6-v2", prefer_remote=True)

    vec = e.embed_query("some text that needs embedding")

    assert e.embedder_id == "hash-v1", f"tag says {e.embedder_id} for a hash vector"
    assert vec == e._hash_embed("some text that needs embedding"), "vector was not the hash fallback"


def test_sync_embeds_files_it_indexes(tmp_path):
    """A note indexed without a vector is keyword-only; sync must embed it."""
    vault = str(tmp_path / "vault")
    mem = UnifiedMemorySystem(vault_path=vault, dsn=str(tmp_path / "g.db"), auto_sync=False)
    mem.vault.write_note("Unindexed Note", "Body written straight to the vault, never remembered.",
                         wing="qa", room="sync")
    mem.remember("Already Indexed", "A body long enough for the admission controller to accept.",
                 wing="qa", room="sync")

    res = mem.sync_vault_to_db()
    assert res["synced"] >= 2

    rows = {r["title"]: r for r in mem.db.list_notes(limit=100)}
    assert rows["Unindexed Note"]["has_embedding"], "synced note has no vector"
    assert rows["Already Indexed"]["has_embedding"]

    # and it is now reachable by semantic search
    hits = mem.recall("written straight to the vault", mode="semantic", top_k=5)
    assert any(h["title"] == "Unindexed Note" for h in hits), "indexed note not semantically reachable"
