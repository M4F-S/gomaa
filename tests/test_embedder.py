import pytest
from mnemosyne.embedder import Embedder


class TestEmbedder:
    def test_embed_single_text(self):
        emb = Embedder()
        vectors = emb.embed(["Hello world"])
        assert len(vectors) == 1
        assert len(vectors[0]) > 0

    def test_embed_empty_list(self):
        emb = Embedder()
        vectors = emb.embed([])
        assert vectors == []

    def test_embed_multiple_texts(self):
        emb = Embedder()
        vectors = emb.embed(["Hello", "World", "Test"])
        assert len(vectors) == 3
