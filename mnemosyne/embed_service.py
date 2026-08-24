"""
Mnemosyne Centralized Embedding Microservice (v3.2)
Lightweight HTTP microservice serving vector embeddings for multi-agent fleets.
Uses ONNX Runtime or SentenceTransformers in a single shared process (~75MB-250MB RAM).
"""

import os
import sys
import logging
from typing import List, Dict, Any, Optional

# Protocol & stdout safety
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("mnemosyne-embed-service")

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


class EmbedRequest(BaseModel):
    texts: List[str]
    model: Optional[str] = "all-MiniLM-L6-v2"


class EmbedResponse(BaseModel):
    embeddings: List[List[float]]
    dim: int
    count: int
    model: str


def create_app(model_name: str = "all-MiniLM-L6-v2"):
    if not HAS_FASTAPI:
        raise RuntimeError("FastAPI and uvicorn are required to run embed-service. Install with: pip install fastapi uvicorn")

    from sentence_transformers import SentenceTransformer
    logger.info(f"Loading embedding model in microservice: {model_name}...")
    model = SentenceTransformer(model_name)
    dim = model.get_sentence_embedding_dimension()
    logger.info(f"Microservice ready (dim={dim}).")

    app = FastAPI(title="Mnemosyne Embedding Service", version="3.2.0")

    @app.get("/health")
    def health():
        return {"status": "healthy", "model": model_name, "dim": dim}

    @app.post("/embed", response_model=EmbedResponse)
    def embed_texts(req: EmbedRequest):
        if not req.texts:
            return EmbedResponse(embeddings=[], dim=dim, count=0, model=model_name)
        try:
            embeddings = model.encode(req.texts, show_progress_bar=False, normalize_embeddings=True)
            return EmbedResponse(
                embeddings=embeddings.tolist(),
                dim=dim,
                count=len(req.texts),
                model=model_name
            )
        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return app


def run_service(host: str = "0.0.0.0", port: int = 8000, model_name: str = "all-MiniLM-L6-v2", workers: int = 1):
    app = create_app(model_name)
    uvicorn.run(app, host=host, port=port, workers=workers, log_level="warning")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    run_service(port=port)
