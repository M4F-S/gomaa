from unittest.mock import MagicMock, patch
from gomaa.embedder import Embedder


class TestEmbedderV32:
    def test_remote_embed_success(self):
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"embeddings": [[0.1] * 384]}
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            embedder = Embedder(embed_url="http://127.0.0.1:8000")
            emb = embedder.embed_query("test query")
            assert len(emb) == 384
            assert emb[0] == 0.1

    def test_circuit_breaker_opens_after_three_failures(self):
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.post.side_effect = RuntimeError("Service Down")
            mock_client_cls.return_value = mock_client

            embedder = Embedder(embed_url="http://127.0.0.1:8000")
            # 3 failures
            embedder.embed_documents(["fail1"])
            embedder.embed_documents(["fail2"])
            embedder.embed_documents(["fail3"])

            assert embedder._failure_count >= 3
            # Graceful hash fallback without throwing
            res = embedder.embed_documents(["fallback"])
            assert len(res) == 1
            assert len(res[0]) == 384
