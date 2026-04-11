from __future__ import annotations

import re
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services import embedder, qdrant_service
from app.services.ollama import build_prompt, query_ollama
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

# Matches a standalone 4-6 digit circular number in the query string
_CIRC_NUMBER_RE = re.compile(r"\b(\d{4,6})\b")

# Context size limits per mode (chars)
_BRIEF_CTX_LIMIT = 2500
_FULL_CTX_LIMIT = 4000   # full mode gets more context; still fits in llama3 window


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]


@router.get("/ask", response_model=QueryResponse, summary="Ask a question about NSE circulars")
def ask(
    q: str = Query(..., min_length=3, description="Your question about NSE circulars"),
    top_k: int = Query(5, ge=1, le=20, description="Number of context chunks to retrieve"),
    mode: Literal["brief", "full"] = Query(
        "brief",
        description=(
            "brief — 2-3 bullet points (default). "
            "full — comprehensive explanation + all matching circulars with details."
        ),
    ),
) -> QueryResponse:
    """
    RAG query pipeline:
    - brief mode: semantic search → 2-3 bullet answer
    - full  mode: semantic search with more chunks → topic explanation + all circulars
    - auto  mode: if query contains a circular number → exact Qdrant filter + structured detail
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # --- Step 1: decide search strategy ---
    circ_match = _CIRC_NUMBER_RE.search(q)

    if circ_match:
        # Circular number in query → exact payload filter, ignore mode
        circ_number = circ_match.group(1)
        logger.info("Circular number detected in query", circ_number=circ_number)
        try:
            hits = qdrant_service.search_by_circ_number(circ_number, top_k=top_k)
        except Exception as exc:
            logger.exception("Circular lookup failed", error=str(exc))
            raise HTTPException(status_code=502, detail=f"Circular lookup error: {exc}")
    else:
        # Topic query → semantic vector search
        # full mode fetches more chunks for a richer answer
        effective_top_k = top_k * 2 if mode == "full" else top_k
        try:
            query_vec = embedder.embed_query(q)
        except Exception as exc:
            logger.error("Embedding failed", error=str(exc))
            raise HTTPException(status_code=500, detail="Embedding error")

        try:
            hits = qdrant_service.search(query_vec, top_k=effective_top_k)
        except Exception as exc:
            logger.exception("Qdrant search failed", error=str(exc))
            raise HTTPException(status_code=502, detail=f"Vector search error: {exc}")

    if not hits:
        return QueryResponse(answer="No relevant circular found", sources=[])

    # --- Step 2: build context ---
    context_parts: list[str] = []
    sources: list[str] = []

    for hit in hits:
        circ_num = hit.get("circNumber", "Unknown")
        subject = hit.get("subject", "")
        text = hit.get("text", "")
        context_parts.append(f"[Circular {circ_num}] {subject}\n{text}")
        if circ_num not in sources:
            sources.append(circ_num)

    context = "\n\n---\n\n".join(context_parts)

    # Auto-detect single-circular dominance using two signals:
    # 1. Score ratio: top hit ≥1.2× the best score from any other circular
    # 2. Top-2 same: both the first and second hits belong to the same circular
    # Either signal is enough to switch to detail mode.
    dominant = False
    if not circ_match and len(hits) >= 1:
        top_circ_num = hits[0].get("circNumber", "")
        top_score = hits[0].get("score", 0)

        other_score = next(
            (h.get("score", 0) for h in hits[1:] if h.get("circNumber") != top_circ_num),
            0,
        )
        score_dominant = (other_score == 0) or (top_score >= other_score * 1.2)

        top2_same = (
            len(hits) >= 2
            and hits[1].get("circNumber") == top_circ_num
        )

        dominant = score_dominant or top2_same
        if dominant:
            logger.info(
                "Single-circular dominance detected",
                circ_number=top_circ_num,
                top_score=round(top_score, 3),
                other_score=round(other_score, 3),
                signal="score" if score_dominant else "top2",
            )

    if circ_match or dominant:
        detail_mode = True
        full_mode = False
        # Keep only chunks from the dominant circular so the LLM sees clean context
        if dominant and not circ_match:
            dominant_num = hits[0].get("circNumber", "")
            dominant_hits = [h for h in hits if h.get("circNumber") == dominant_num]
            context_parts = [
                f"[Circular {h.get('circNumber')}] {h.get('subject','')}\n{h.get('text','')}"
                for h in dominant_hits
            ]
            context = "\n\n---\n\n".join(context_parts)
            sources = [dominant_num]
    elif mode == "full":
        detail_mode = False
        full_mode = True
        if len(context) > _FULL_CTX_LIMIT:
            context = context[:_FULL_CTX_LIMIT] + "\n[context truncated]"
    else:
        detail_mode = False
        full_mode = False
        if len(context) > _BRIEF_CTX_LIMIT:
            context = context[:_BRIEF_CTX_LIMIT] + "\n[context truncated]"

    # --- Step 3: query Ollama ---
    try:
        prompt = build_prompt(
            context=context,
            question=q,
            detail_mode=detail_mode,
            full_mode=full_mode,
        )
        answer = query_ollama(prompt)
    except RuntimeError as exc:
        logger.error("Ollama query failed", error=str(exc))
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error querying Ollama", error=str(exc))
        raise HTTPException(status_code=500, detail="LLM error")

    formatted_sources = [f"NSE/CIRCULAR/{s}" for s in sources]
    return QueryResponse(answer=answer, sources=formatted_sources)
