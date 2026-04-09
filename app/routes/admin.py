from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.mongo import get_collection
from app.services.qdrant_service import get_client
from app.config import settings
from app.utils.logger import get_logger

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = get_logger(__name__)


class CleanResponse(BaseModel):
    status: str
    mongo_deleted: int
    qdrant_collection_recreated: bool


@router.delete("/clean", response_model=CleanResponse, summary="Wipe all ingested data")
def clean_all() -> CleanResponse:
    """
    Delete all circulars from MongoDB and drop + recreate the Qdrant collection.
    This is irreversible — use with caution.
    """
    # --- MongoDB ---
    try:
        col = get_collection()
        result = col.delete_many({})
        mongo_deleted = result.deleted_count
        logger.info("Cleared MongoDB collection", deleted=mongo_deleted)
    except Exception as exc:
        logger.error("MongoDB cleanup failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"MongoDB cleanup failed: {exc}")

    # --- Qdrant ---
    try:
        client = get_client()
        existing = {c.name for c in client.get_collections().collections}
        if settings.qdrant_collection in existing:
            client.delete_collection(settings.qdrant_collection)
            logger.info("Deleted Qdrant collection", name=settings.qdrant_collection)

        from qdrant_client.http import models as qm
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=qm.VectorParams(
                size=settings.vector_size,
                distance=qm.Distance.COSINE,
            ),
        )
        logger.info("Recreated Qdrant collection", name=settings.qdrant_collection)
        qdrant_ok = True
    except Exception as exc:
        logger.error("Qdrant cleanup failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Qdrant cleanup failed: {exc}")

    return CleanResponse(
        status="ok",
        mongo_deleted=mongo_deleted,
        qdrant_collection_recreated=qdrant_ok,
    )
