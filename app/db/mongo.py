from __future__ import annotations

from typing import Any

import pymongo
from pymongo import MongoClient
from pymongo.collection import Collection

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(settings.mongo_uri)
        logger.info("MongoDB client created", uri=settings.mongo_uri)
    return _client


def get_collection() -> Collection:
    client = get_client()
    db = client[settings.mongo_db]
    return db[settings.mongo_collection]


def upsert_circular(circular: dict[str, Any]) -> bool:
    """
    Insert or update a circular document by circNumber.
    Returns True if inserted (new), False if updated (existing).
    """
    col = get_collection()
    circ_number = circular.get("circNumber") or circular.get("circno")

    result = col.update_one(
        {"circNumber": circ_number},
        {"$set": circular},
        upsert=True,
    )

    is_new = result.upserted_id is not None
    logger.info(
        "Upserted circular",
        circ_number=circ_number,
        is_new=is_new,
    )
    return is_new


def circular_exists(circ_number: str) -> bool:
    """Check if a circular already has its PDF processed (embeddings stored)."""
    col = get_collection()
    doc = col.find_one({"circNumber": circ_number, "embedded": True})
    return doc is not None


def mark_embedded(circ_number: str) -> None:
    """Mark a circular as fully processed and embedded."""
    col = get_collection()
    col.update_one(
        {"circNumber": circ_number},
        {"$set": {"embedded": True}},
    )
    logger.info("Marked circular as embedded", circ_number=circ_number)


def close_client() -> None:
    global _client
    if _client:
        _client.close()
        _client = None
        logger.info("MongoDB client closed")
