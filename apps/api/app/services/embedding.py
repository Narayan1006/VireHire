"""
VeriHire v2 - Embedding Service using fastembed BAAI/bge-small-en-v1.5
Uses apps/api/.model_cache for model weights and applies query instruction prefix
as recommended by the BAAI/bge-small-en-v1.5 model card for retrieval tasks.
"""

from pathlib import Path
from typing import List, Sequence
from fastembed import TextEmbedding

MODEL_NAME = "BAAI/bge-small-en-v1.5"
MODEL_CACHE_DIR = (Path(__file__).resolve().parent.parent.parent / ".model_cache").resolve()

# BGE retrieval instruction prefix as recommended in BAAI/bge model card:
# "For retrieval, you need to add instruction to each query:
# 'Represent this sentence for searching relevant passages: ' (for passages, no instruction needed)."
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

_model = None


def get_embedding_model() -> TextEmbedding:
    global _model
    if _model is None:
        MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _model = TextEmbedding(
            model_name=MODEL_NAME,
            cache_dir=str(MODEL_CACHE_DIR),
        )
    return _model


def compute_embeddings(texts: Sequence[str], batch_size: int = 16) -> List[List[float]]:
    """
    Generates 384-dimensional dense vectors for a sequence of candidate texts.
    Default batch size is 16 to stay within memory limits (under 450 MB on Render free tier).
    """
    if not texts:
        return []
    model = get_embedding_model()
    embeddings = list(model.embed(texts, batch_size=batch_size))
    return [e.tolist() if hasattr(e, "tolist") else list(e) for e in embeddings]


def compute_query_embedding(query: str) -> List[float]:
    """
    Computes a dense vector for a query string, applying the official BGE query instruction prefix.
    """
    cleaned_query = query.strip()
    prefixed_query = f"{BGE_QUERY_PREFIX}{cleaned_query}"
    embeddings = compute_embeddings([prefixed_query], batch_size=1)
    return embeddings[0] if embeddings else [0.0] * 384
