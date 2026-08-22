"""Embedding engine with 3-tier fallback."""

import os
import json
import hashlib
import logging
import threading
from typing import List, Optional, Any

logger = logging.getLogger("unified-memory")

EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "384"))
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")


class Embedder:
    """
    Generate vector embeddings for text.

    Tier 1: sentence-transformers (local, no API calls)
    Tier 2: Ollama API (local LLM server)
    Tier 3: Deterministic hash-based projection (zero dependencies)
    """

    def __init__(self, model_name: str = EMBEDDING_MODEL, dim: int = EMBEDDING_DIM) -> None:
        self.model_name = model_name
        self.dim = dim
        self._model: Optional[Any] = None
        self._provider: Optional[str] = None
        self._lock = threading.Lock()
        self._init_provider()

    def _init_provider(self) -> None:
        """Try embedding providers in order."""
        # Tier 1: sentence-transformers
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
            self._provider = "sentence-transformers"
            logger.info(f"Embedder: using sentence-transformers ({self.model_name})")
            return
        except Exception as e:
            logger.warning(f"sentence-transformers unavailable: {e}")

        # Tier 2: Ollama
        try:
            import urllib.request

            req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    self._provider = "ollama"
                    logger.info(f"Embedder: using Ollama at {OLLAMA_URL}")
                    return
        except Exception as e:
            logger.warning(f"Ollama unavailable: {e}")

        # Tier 3: deterministic hash fallback
        self._provider = "hash"
        logger.info("Embedder: using deterministic hash fallback (no external deps)")

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts into vectors."""
        if not texts:
            return []

        with self._lock:
            if self._provider == "sentence-transformers":
                try:
                    assert self._model is not None
                    vectors = self._model.encode(texts, convert_to_numpy=True)
                    return [self._normalize(v.tolist()) for v in vectors]
                except Exception as e:
                    logger.error(f"sentence-transformers failed: {e}, falling back")
                    self._provider = "hash"

            if self._provider == "ollama":
                try:
                    import urllib.request

                    results = []
                    for text in texts:
                        body = json.dumps({"model": self.model_name, "prompt": text}).encode()
                        req = urllib.request.Request(
                            f"{OLLAMA_URL}/api/embeddings",
                            data=body,
                            headers={"Content-Type": "application/json"},
                            method="POST",
                        )
                        with urllib.request.urlopen(req, timeout=30) as resp:
                            data = json.loads(resp.read())
                            results.append(self._normalize(data.get("embedding", [])))
                    return results
                except Exception as e:
                    logger.error(f"Ollama failed: {e}, falling back")
                    self._provider = "hash"

        # Hash fallback: deterministic, no external deps
        return [self._hash_embed(t) for t in texts]

    def _hash_embed(self, text: str) -> List[float]:
        """Deterministic embedding via hash-based random projection."""
        vec = [0.0] * self.dim
        for i in range(self.dim):
            h = hashlib.sha256(f"{text}::dim{i}".encode()).hexdigest()
            val = int(h[:8], 16) / 0xFFFFFFFF
            vec[i] = val * 2 - 1
        norm = sum(x * x for x in vec) ** 0.5
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    def _normalize(self, vec: List[float]) -> List[float]:
        """Pad/truncate and L2-normalize a vector."""
        vec = list(vec)
        if len(vec) < self.dim:
            vec.extend([0.0] * (self.dim - len(vec)))
        elif len(vec) > self.dim:
            vec = vec[: self.dim]
        norm = sum(x * x for x in vec) ** 0.5
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec
