from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.ingest import run_ingestion
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


class IngestResponse(BaseModel):
    status: str
    total_fetched: int
    new_in_mongo: int
    skipped_already_embedded: int
    processed: int
    failed: int
    total_chunks: int


@router.post("/ingest", response_model=IngestResponse, summary="Ingest NSE circulars")
def ingest() -> IngestResponse:
    """
    Trigger the full ingestion pipeline:
    - Fetch NSE circulars
    - Store metadata in MongoDB
    - Extract PDF text, chunk, embed, and store in Qdrant
    """
    try:
        summary = run_ingestion()
    except RuntimeError as exc:
        logger.error("Ingestion failed", error=str(exc))
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected ingestion error", error=str(exc))
        raise HTTPException(status_code=500, detail="Internal ingestion error")

    return IngestResponse(status="ok", **summary)
