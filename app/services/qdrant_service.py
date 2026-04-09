from __future__ import annotations

import uuid
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_client: QdrantClient | None = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        logger.info(
            "Qdrant client created",
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
    return _client


def ensure_collection() -> None:
    """Create the Qdrant collection if it does not already exist."""
    client = get_client()
    existing = {col.name for col in client.get_collections().collections}

    if settings.qdrant_collection not in existing:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=qdrant_models.VectorParams(
                size=settings.vector_size,
                distance=qdrant_models.Distance.COSINE,
            ),
        )
        logger.info("Created Qdrant collection", name=settings.qdrant_collection)
    else:
        logger.info("Qdrant collection already exists", name=settings.qdrant_collection)


def store_chunks(
    chunks: list[str],
    embeddings: list[list[float]],
    circular_meta: dict[str, Any],
) -> int:
    """
    Upload chunk embeddings to Qdrant with circular metadata as payload.

    Args:
        chunks: Raw text chunks.
        embeddings: Corresponding embedding vectors.
        circular_meta: Metadata dict (circNumber, subject, date, file link).

    Returns:
        Number of points uploaded.
    """
    if not chunks or not embeddings:
        return 0

    client = get_client()

    points = [
        qdrant_models.PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "text": chunk,
                "circNumber": circular_meta.get("circNumber", ""),
                # NSE uses 'sub' for subject and 'cirDate' for date
                "subject": (
                    circular_meta.get("sub")
                    or circular_meta.get("subject", "")
                ),
                "date": (
                    circular_meta.get("cirDate")
                    or circular_meta.get("circDate")
                    or circular_meta.get("date", "")
                ),
                "fileLink": (
                    circular_meta.get("circFilelink")
                    or circular_meta.get("filelink", "")
                ),
            },
        )
        for chunk, embedding in zip(chunks, embeddings)
    ]

    client.upsert(collection_name=settings.qdrant_collection, points=points)
    logger.info(
        "Stored chunk embeddings",
        circ_number=circular_meta.get("circNumber"),
        num_points=len(points),
    )
    return len(points)


def search(query_vector: list[float], top_k: int = 5) -> list[dict[str, Any]]:
    """
    Semantic vector search — returns the top-k most relevant chunks.
    """
    client = get_client()
    response = client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_vector,
        limit=top_k,
        with_payload=True,
    )

    hits: list[dict[str, Any]] = []
    for hit in response.points:
        payload = dict(hit.payload or {})
        payload["score"] = hit.score
        hits.append(payload)

    logger.info("Qdrant search completed", top_k=top_k, hits=len(hits))
    return hits


def search_by_circ_number(circ_number: str, top_k: int = 10) -> list[dict[str, Any]]:
    """
    Exact payload filter lookup — returns all chunks that belong to a specific
    circular number. Used when the query explicitly names a circular number.
    """
    client = get_client()

    # circNumber is stored as string in payload — match both forms to be safe
    circ_filter = qdrant_models.Filter(
        should=[
            qdrant_models.FieldCondition(
                key="circNumber",
                match=qdrant_models.MatchValue(value=circ_number),  # string
            ),
            qdrant_models.FieldCondition(
                key="circNumber",
                match=qdrant_models.MatchValue(value=int(circ_number)),  # int
            ),
        ]
    )

    # scroll (no vector needed) — just fetch matching points by payload
    results, _ = client.scroll(
        collection_name=settings.qdrant_collection,
        scroll_filter=circ_filter,
        limit=top_k,
        with_payload=True,
        with_vectors=False,
    )

    hits: list[dict[str, Any]] = []
    for point in results:
        payload = dict(point.payload or {})
        hits.append(payload)

    logger.info(
        "Circular number lookup completed",
        circ_number=circ_number,
        hits=len(hits),
    )
    return hits
