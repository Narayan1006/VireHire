"""
VeriHire AI - Embedding Generator

Wraps the sentence-transformers library to generate 384-dimensional
embeddings for resume text chunks and job descriptions.

Uses model: all-MiniLM-L6-v2
Supports single-text and batch embedding with retry logic.

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
"""

import time
from typing import List, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Defaults
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384
DEFAULT_BATCH_SIZE = 64
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds


class Embedder:
    """
    Generate embeddings using sentence-transformers.

    Lazily loads the model on first use to avoid slow imports at startup.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ):
        self.model_name = model_name
        self.batch_size = batch_size
        self._model = None  # Lazy-loaded

    @property
    def model(self):
        """Lazy-load the sentence-transformers model."""
        if self._model is None:
            logger.info("Loading embedding model: %s", self.model_name)
            start = time.time()
            from sentence_transformers import SentenceTransformer
            import torch

            # Determine device (GPU if available, else CPU)
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info("Using device: %s", device)
            if device == "cuda":
                logger.info("GPU: %s", torch.cuda.get_device_name(0))

            self._model = SentenceTransformer(self.model_name, device=device)
            elapsed = time.time() - start
            
            # Get embedding dimension (compatible with different sentence-transformers versions)
            try:
                dim = self._model.get_sentence_embedding_dimension()
            except AttributeError:
                dim = EMBEDDING_DIMENSION  # fallback to known dimension
            
            logger.info(
                "Embedding model loaded in %.2fs (dim=%d, device=%s)",
                elapsed,
                dim,
                device,
            )
        return self._model

    def embed_text(self, text: str) -> List[float]:
        """
        Generate a 384-dimensional embedding for a single text.

        Args:
            text: Input text string.

        Returns:
            List of floats (384 dimensions).

        Raises:
            RuntimeError: If embedding fails after MAX_RETRIES attempts.
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding, returning zero vector")
            return [0.0] * EMBEDDING_DIMENSION

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                embedding = self.model.encode(
                    text,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                )
                result = embedding.tolist()

                assert len(result) == EMBEDDING_DIMENSION, (
                    f"Expected {EMBEDDING_DIMENSION} dims, got {len(result)}"
                )

                return result

            except Exception as e:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "Embedding failed (attempt %d/%d): %s. Retrying in %.1fs...",
                    attempt,
                    MAX_RETRIES,
                    str(e),
                    delay,
                )
                if attempt < MAX_RETRIES:
                    time.sleep(delay)

        raise RuntimeError(
            f"Embedding generation failed after {MAX_RETRIES} retries"
        )

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts.

        Processes in sub-batches of self.batch_size (default 64) for
        memory efficiency.

        Args:
            texts: List of input text strings.

        Returns:
            List of embedding vectors (each 384 dimensions).

        Raises:
            RuntimeError: If embedding fails after MAX_RETRIES attempts.
        """
        if not texts:
            return []

        # Replace empty texts with a placeholder
        cleaned = [t if t and t.strip() else "empty" for t in texts]

        all_embeddings: List[List[float]] = []
        total = len(cleaned)

        for start_idx in range(0, total, self.batch_size):
            end_idx = min(start_idx + self.batch_size, total)
            batch = cleaned[start_idx:end_idx]

            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    embeddings = self.model.encode(
                        batch,
                        convert_to_numpy=True,
                        show_progress_bar=False,
                        batch_size=len(batch),
                    )

                    batch_results = embeddings.tolist()

                    # Validate dimensions
                    for emb in batch_results:
                        assert len(emb) == EMBEDDING_DIMENSION, (
                            f"Expected {EMBEDDING_DIMENSION} dims, got {len(emb)}"
                        )

                    all_embeddings.extend(batch_results)

                    logger.debug(
                        "Embedded batch %d-%d of %d (%d texts)",
                        start_idx + 1,
                        end_idx,
                        total,
                        len(batch),
                    )
                    break  # Success, move to next batch

                except Exception as e:
                    delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        "Batch embedding failed (attempt %d/%d, batch %d-%d): %s",
                        attempt,
                        MAX_RETRIES,
                        start_idx + 1,
                        end_idx,
                        str(e),
                    )
                    if attempt < MAX_RETRIES:
                        time.sleep(delay)
                    else:
                        raise RuntimeError(
                            f"Batch embedding failed after {MAX_RETRIES} retries "
                            f"(batch {start_idx + 1}-{end_idx})"
                        )

        assert len(all_embeddings) == total, (
            f"Expected {total} embeddings, got {len(all_embeddings)}"
        )

        return all_embeddings
