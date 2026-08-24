"""
Embedder Module for Mnemosyne (v3.2)
Supports:
1. High-efficiency Remote Microservice (MEMORY_EMBED_URL) with connection reuse & circuit breaker.
2. Zero-RAM Fallback Mode (Graceful degradation for multi-agent fleets).
3. Local SentenceTransformers (for standalone single-user workstations).
4. Deterministic Hash Fallback.
"""

import os
import sys
import hashlib
import time
import logging
from typing import List, Optional

# Disable tokenizer parallelism and progress bars to keep stdio stream pristine
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("mnemosyne-embedder")


class CircuitBreakerOpen(Exception):
    pass


class Embedder:
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        embed_url: Optional[str] = None,
        prefer_remote: bool = True
    ):
        self.model_name = model_name
        self.dim = 384
        self._provider = None
        self._local_model = None

        # Remote microservice settings
        self.embed_url = embed_url or os.environ.get("MEMORY_EMBED_URL")
        self._prefer_remote = prefer_remote and bool(self.embed_url)
        self._http_client = None

        # Circuit breaker state
        self._failure_count = 0
        self._circuit_open_until = 0.0
        self._failure_threshold = 3
        self._recovery_timeout = 30.0

        if self.embed_url:
            self._provider = "remote-http"
            logger.info(f"Embedder: configured remote microservice at {self.embed_url}")
            try:
                import httpx
                self._http_client = httpx.Client(
                    timeout=httpx.Timeout(connect=1.0, read=3.0, write=1.0, pool=5.0),
                    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
                )
            except ImportError:
                self._http_client = None
        else:
            self._init_local_model()

    def _init_local_model(self):
        try:
            from sentence_transformers import SentenceTransformer
            self._local_model = SentenceTransformer(self.model_name)
            self._provider = "sentence-transformers"
            try:
                self.dim = self._local_model.get_embedding_dimension()
            except AttributeError:
                self.dim = self._local_model.get_sentence_embedding_dimension()
            logger.info(f"Embedder: using local sentence-transformers ({self.model_name})")
        except ImportError:
            self._provider = "hash-fallback"
            logger.warning("Embedder: sentence-transformers not found; using deterministic hash fallback.")

    def _check_circuit(self):
        if time.time() < self._circuit_open_until:
            raise CircuitBreakerOpen("Embedding microservice circuit breaker is OPEN")

    def _record_success(self):
        self._failure_count = 0
        self._circuit_open_until = 0.0

    def _record_failure(self):
        self._failure_count += 1
        if self._failure_count >= self._failure_threshold:
            self._circuit_open_until = time.time() + self._recovery_timeout
            logger.warning(f"Embedding circuit breaker OPEN for {self._recovery_timeout}s after {self._failure_count} failures.")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        # 1. Try Remote Microservice if configured
        if self.embed_url:
            try:
                self._check_circuit()
                return self._embed_remote(texts)
            except Exception as e:
                self._record_failure()
                logger.warning(f"Remote embedding call failed ({e}); degrading gracefully.")
                # If remote fails, do NOT load PyTorch into RAM on fleet nodes — use hash fallback
                if self._local_model is None:
                    return [self._hash_embed(t) for t in texts]

        # 2. Local Model (for standalone developer workstations)
        if self._local_model is not None:
            try:
                embeddings = self._local_model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
                return embeddings.tolist()
            except Exception as e:
                logger.error(f"Local embedding error: {e}")
                return [self._hash_embed(t) for t in texts]

        # 3. Deterministic Hash Fallback
        return [self._hash_embed(t) for t in texts]

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Alias for embed_documents for backwards compatibility."""
        return self.embed_documents(texts)

    def _embed_remote(self, texts: List[str]) -> List[List[float]]:
        payload = {"texts": texts, "model": self.model_name}
        url = f"{self.embed_url.rstrip('/')}/embed"

        if self._http_client is not None:
            resp = self._http_client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            self._record_success()
            return data["embeddings"]
        else:
            import urllib.request
            import json
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=3.0) as response:
                data = json.loads(response.read().decode("utf-8"))
                self._record_success()
                return data["embeddings"]

    def embed_query(self, text: str) -> List[float]:
        results = self.embed_documents([text])
        return results[0] if results else [0.0] * self.dim

    def _hash_embed(self, text: str) -> List[float]:
        """Deterministic 384-dimensional normalized vector hash."""
        vec = []
        for i in range(self.dim):
            h = hashlib.sha256(f"{text}:{i}".encode("utf-8")).hexdigest()
            val = (int(h[:8], 16) / 0xFFFFFFFF) * 2.0 - 1.0
            vec.append(val)
        norm = sum(x * x for x in vec) ** 0.5
        return [x / norm for x in vec] if norm > 0 else vec
