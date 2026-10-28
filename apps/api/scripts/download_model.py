"""
Downloads and caches the fastembed BAAI/bge-small-en-v1.5 model during build time.
"""

from pathlib import Path
from fastembed import TextEmbedding

MODEL_NAME = "BAAI/bge-small-en-v1.5"
CACHE_DIR = Path(__file__).resolve().parent.parent / ".model_cache"


def download():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {MODEL_NAME} to {CACHE_DIR}...")
    model = TextEmbedding(model_name=MODEL_NAME, cache_dir=str(CACHE_DIR))
    list(model.embed(["test warmup sentence"]))
    print(f"Model {MODEL_NAME} downloaded and cached successfully at {CACHE_DIR}.")


if __name__ == "__main__":
    download()
