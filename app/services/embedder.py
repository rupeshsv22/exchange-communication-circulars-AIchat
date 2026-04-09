from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    """Load the embedding model once and cache it for the process lifetime."""
    logger.info("Loading embedding model", model=settings.embedding_model)
    model = SentenceTransformer(settings.embedding_model)
    logger.info("Embedding model loaded")
    return model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Encode a list of text strings into embedding vectors using batch inference.

    Args:
        texts: List of strings to embed.

    Returns:
        List of float vectors, one per input string.
    """
    if not texts:
        return []

    model = get_model()
    # convert_to_numpy=False → returns Python lists directly
    embeddings = model.encode(texts, batch_size=32, show_progress_bar=False)
    logger.info("Generated embeddings", count=len(texts))
    return [emb.tolist() for emb in embeddings]


def embed_query(query: str) -> list[float]:
    """Embed a single query string."""
    return embed_texts([query])[0]
