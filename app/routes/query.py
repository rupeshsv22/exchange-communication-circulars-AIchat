from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services import embedder, qdrant_service
from app.services.ollama import build_prompt, query_ollama
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

# Matches a standalone 4-6 digit circular number in the query string
_CIRC_NUMBER_RE = re.compile(r"\b(\d{4,6})\b")


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]  # list of circNumbers used as context


@router.get("/ask", response_model=QueryResponse, summary="Ask a question about NSE circulars")
def ask(
    q: str = Query(..., min_length=3, description="Your question about NSE circulars"),
    top_k: int = Query(5, ge=1, le=20, description="Number of context chunks to retrieve"),
) -> QueryResponse:
    """
    RAG query pipeline:
    1. Embed the user question
    2. Search Qdrant for the top-k relevant chunks
    3. Build a context string from the hits
    4. Send prompt to Ollama and return the answer
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # Step 1: check if query explicitly names a circular number
    circ_match = _CIRC_NUMBER_RE.search(q)

    if circ_match:
        # Exact lookup by circular number — skip embedding entirely
        circ_number = circ_match.group(1)
        logger.info("Circular number detected in query", circ_number=circ_number)
        try:
            hits = qdrant_service.search_by_circ_number(circ_number, top_k=top_k)
        except Exception as exc:
            logger.exception("Circular lookup failed", error=str(exc))
            raise HTTPException(status_code=502, detail=f"Circular lookup error: {exc}")
    else:
        # Semantic vector search
        try:
            query_vec = embedder.embed_query(q)
        except Exception as exc:
            logger.error("Embedding failed", error=str(exc))
            raise HTTPException(status_code=500, detail="Embedding error")

        try:
            hits = qdrant_service.search(query_vec, top_k=top_k)
        except Exception as exc:
            logger.exception("Qdrant search failed", error=str(exc))
            raise HTTPException(status_code=502, detail=f"Vector search error: {exc}")

    if not hits:
        return QueryResponse(answer="No relevant circular found", sources=[])

    # Step 3: build context and collect source circular numbers
    context_parts: list[str] = []
    sources: list[str] = []

    for hit in hits:
        circ_number = hit.get("circNumber", "Unknown")
        subject = hit.get("subject", "")
        text = hit.get("text", "")

        context_parts.append(
            f"[Circular {circ_number}] {subject}\n{text}"
        )
        if circ_number not in sources:
            sources.append(circ_number)

    context = "\n\n---\n\n".join(context_parts)

    # For circular number lookups, send full context and use the detail prompt.
    # For general queries, cap at 2500 chars to stay within llama3's context window.
    detail_mode = circ_match is not None
    if not detail_mode and len(context) > 2500:
        context = context[:2500] + "\n[context truncated]"

    # Step 4: query Ollama
    try:
        prompt = build_prompt(context=context, question=q, detail_mode=detail_mode)
        answer = query_ollama(prompt)
    except RuntimeError as exc:
        logger.error("Ollama query failed", error=str(exc))
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error querying Ollama", error=str(exc))
        raise HTTPException(status_code=500, detail="LLM error")

    formatted_sources = [f"NSE/CIRCULAR/{s}" for s in sources]
    return QueryResponse(answer=answer, sources=formatted_sources)
