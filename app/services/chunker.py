from __future__ import annotations

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def chunk_text(
    text: str,
    chunk_size: int = settings.chunk_size,
    overlap: int = settings.chunk_overlap,
) -> list[str]:
    """
    Split text into overlapping fixed-size character chunks.

    Args:
        text: Raw text to split.
        chunk_size: Maximum characters per chunk (default from config).
        overlap: Overlap characters between consecutive chunks (default from config).

    Returns:
        List of text chunks. Empty list if text is empty.
    """
    text = text.strip()
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    step = chunk_size - overlap  # advance by this many chars each iteration

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start += step

    logger.info("Chunked text", total_chars=len(text), num_chunks=len(chunks))
    return chunks
