"""
Gomaa Centralized Embedding Microservice (v3.5.0).
FastAPI microservice hosting sentence-transformers in a single dedicated process (~75MB RAM).
"""

import logging
import os
import sys
from typing import List

try:
    from pydantic import BaseModel
except ImportError:
    BaseModel = type("BaseModel", (), {})

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("gomaa-embed-service")

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
            "Install with: pip install 'gomaa-memory[embed-service]'"
        )

    logger.info(f"Loading embedding model: {model_name}...")
    model = SentenceTransformer(model_name)
    logger.info(f"Embedding model {model_name} loaded successfully (dim={model.get_sentence_embedding_dimension()}).")

    app = FastAPI(title="Gomaa Embedding Service", version="3.5.0")

    @app.get("/health")
    def health():
        return {
            "status": "healthy",
            "model": model_name,
            "dim": model.get_sentence_embedding_dimension(),
            "service": "gomaa-embed-service",
            "version": "3.5.0",
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


def run_service(
    host: str = "0.0.0.0",
    port: int = 8000,
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
) -> None:
    """Run the embedding microservice with explicit host/port/model bindings."""
    import uvicorn

    app = create_app(model_name=model_name)
    logger.info(f"Starting Gomaa Embedding Microservice on {host}:{port}...")
    uvicorn.run(app, host=host, port=port, log_level="info")


def main():
    """Entry point: honors EMBED_SERVICE_PORT / PORT / EMBED_SERVICE_HOST / HOST / EMBED_MODEL env vars."""
    port = int(os.environ.get("EMBED_SERVICE_PORT", os.environ.get("PORT", "8000")))
    host = os.environ.get("EMBED_SERVICE_HOST", os.environ.get("HOST", "0.0.0.0"))
    model_name = os.environ.get("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    run_service(host=host, port=port, model_name=model_name)


if __name__ == "__main__":
    main()