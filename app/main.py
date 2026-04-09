from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.routes.admin import router as admin_router
from app.routes.ingest import router as ingest_router
from app.routes.query import router as query_router
from app.services import qdrant_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: ensure Qdrant collection exists."""
    logger.info("Starting NSE Circulars RAG API")
    try:
        qdrant_service.ensure_collection()
    except Exception as exc:
        logger.warning("Could not connect to Qdrant on startup", error=str(exc))
    yield
    logger.info("Shutting down NSE Circulars RAG API")


app = FastAPI(
    title="NSE Circulars RAG API",
    description=(
        "Retrieval-Augmented Generation system for NSE circulars. "
        "Ingest circulars via POST /ingest, then query via GET /ask."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(ingest_router, tags=["Ingestion"])
app.include_router(query_router, tags=["Query"])
app.include_router(admin_router)


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
