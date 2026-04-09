from __future__ import annotations

from typing import Any

from app.db import mongo
from app.services import chunker, embedder, nse, pdf, qdrant_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _build_metadata_text(circ: dict[str, Any]) -> str:
    """
    Build a plain-text summary from circular metadata fields.
    Used as a fallback when the PDF cannot be downloaded or parsed,
    so the circular is still indexed and searchable in Qdrant.
    """
    parts = [
        f"Circular Number: {circ.get('circNumber', '')}",
        f"Display No: {circ.get('circDisplayNo', '')}",
        f"Subject: {circ.get('sub') or circ.get('subject', '')}",
        f"Category: {circ.get('circCategory', '')}",
        f"Department: {circ.get('circDepartment', '')}",
        f"Date: {circ.get('cirDate') or circ.get('circDate', '')}",
        f"File: {circ.get('circFilelink') or circ.get('filelink', '')}",
    ]
    return "\n".join(p for p in parts if not p.endswith(": "))


def run_ingestion() -> dict[str, Any]:
    """
    Full ingestion pipeline:
      1. Fetch NSE circulars
      2. Deduplicate within batch
      3. Upsert metadata to MongoDB
      4. Skip circulars already embedded
      5. Download PDF → extract text → chunk → embed → store in Qdrant
      6. Mark circular as embedded in MongoDB

    Returns a summary dict with counts.
    """
    # Step 1: ensure Qdrant collection is ready
    qdrant_service.ensure_collection()

    # Step 2: fetch & deduplicate
    raw_circulars = nse.fetch_circulars()
    circulars = nse.deduplicate(raw_circulars)

    summary = {
        "total_fetched": len(circulars),
        "new_in_mongo": 0,
        "skipped_already_embedded": 0,
        "processed": 0,
        "failed": 0,
        "total_chunks": 0,
    }

    for circ in circulars:
        circ_number: str = circ.get("circNumber") or circ.get("circno") or ""

        # Step 3: upsert metadata to MongoDB
        is_new = mongo.upsert_circular(circ)
        if is_new:
            summary["new_in_mongo"] += 1

        # Step 4: skip if already embedded
        if mongo.circular_exists(circ_number):
            logger.info("Skipping already-embedded circular", circ_number=circ_number)
            summary["skipped_already_embedded"] += 1
            continue

        # Step 5a: download & extract PDF text
        text = pdf.process_circular_pdf(circ)

        if not text:
            # PDF failed — build a metadata-only chunk so the circular is
            # still searchable by number/subject in Qdrant
            logger.warning(
                "No PDF text; storing metadata chunk for circular",
                circ_number=circ_number,
            )
            text = _build_metadata_text(circ)
            summary["failed"] += 1  # count as failed PDF but still embed

        # Step 5b: chunk
        chunks = chunker.chunk_text(text)
        if not chunks:
            logger.warning("No chunks generated; skipping circular", circ_number=circ_number)
            continue

        # Step 5c: batch embed
        embeddings = embedder.embed_texts(chunks)

        # Step 5d: store in Qdrant
        n_stored = qdrant_service.store_chunks(chunks, embeddings, circ)
        summary["total_chunks"] += n_stored

        # Step 6: mark embedded
        mongo.mark_embedded(circ_number)
        summary["processed"] += 1

        logger.info(
            "Circular ingested",
            circ_number=circ_number,
            chunks=n_stored,
        )

    logger.info("Ingestion complete", **summary)
    return summary
