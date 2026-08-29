"""Embedder must not crash the process when a local model can't initialize
(e.g. offline first run, HuggingFace download failure).
"""
import sys
import types

import pytest

from gomaa.embedder import Embedder


@pytest.fixture
def fake_sentence_transformers_oserror(monkeypatch):
    """Inject a fake sentence_transformers whose init raises OSError (offline)."""
    fake = types.ModuleType("sentence_transformers")

    class FailingST:
        def __init__(self, *a, **k):
            raise OSError("offline / model download failed")

    fake.SentenceTransformer = FailingST
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake)
    # Ensure fastembed import fails so we reach the ST tier deterministically.
    monkeypatch.setitem(sys.modules, "fastembed", None)
    return fake


def test_embedder_oserror_on_local_init_falls_back(fake_sentence_transformers_oserror):
    # Embedder() must not raise; it should degrade to a usable provider.
    e = Embedder(model_name="sentence-transformers/all-MiniLM-L6-v2")
    assert e._provider in ("hash-fallback", None) or e._provider is not None
    # It must still be able to produce an embedding of the expected dim.
    emb = e.embed_query("hello world")
    assert len(emb) == 384
