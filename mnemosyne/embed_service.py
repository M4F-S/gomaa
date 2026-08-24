"""
Mnemosyne Centralized Embedding Microservice (v3.4.0).
FastAPI microservice hosting sentence-transformers in a single dedicated process (~75MB RAM).
"""

import logging
import os
import sys
from typing import List
from pydantic import BaseModel

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("mnemosyne-embed-service")

try:
    from fastapi import FastAPI, HTTPException
    from sentence_transformers import SentenceTransformer
except ImportError:
    FastAPI = None
    SentenceTransformer = None


class EmbedRequest(BaseModel):
    texts: List[str]


class EmbedResponse(BaseModel):
    embeddings: List[List[float]]
    model: str
    dim: int


def create_app(model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> "FastAPI":
    if FastAPI is None or SentenceTransformer is None:
        raise ImportError(
            "FastAPI and sentence-transformers are required to run the embedding service. "
            "Install with: pip install 'mnemosyne-memory[embed-service]'"
        )

    logger.info(f"Loading embedding model: {model_name}...")
    model = SentenceTransformer(model_name)
    logger.info(f"Embedding model {model_name} loaded successfully (dim={model.get_sentence_embedding_dimension()}).")

    app = FastAPI(title="Mnemosyne Embedding Service", version="3.4.0")

    @app.get("/health")
    def health():
        return {
            "status": "healthy",
            "model": model_name,
            "dim": model.get_sentence_embedding_dimension(),
            "service": "mnemosyne-embed-service",
            "version": "3.4.0",
        }

    @app.post("/embed", response_model=EmbedResponse)
    def embed_texts(req: EmbedRequest):
        if not req.texts:
            return EmbedResponse(embeddings=[], model=model_name, dim=model.get_sentence_embedding_dimension())
        try:
            embs = model.encode(req.texts, normalize_embeddings=True).tolist()
            return EmbedResponse(
                embeddings=embs,
                model=model_name,
                dim=model.get_sentence_embedding_dimension(),
            )
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return app


def main():
    import uvicorn

    port = int(os.environ.get("EMBED_SERVICE_PORT", "8765"))
    host = os.environ.get("EMBED_SERVICE_HOST", "0.0.0.0")
    model_name = os.environ.get("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

    app = create_app(model_name=model_name)
    logger.info(f"Starting Mnemosyne Embedding Microservice on {host}:{port}...")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
