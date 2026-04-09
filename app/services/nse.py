from __future__ import annotations

import time
from typing import Any

import httpx

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# NSE requires browser-like headers to avoid bot blocking
NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
    "Connection": "keep-alive",
}


def fetch_circulars() -> list[dict[str, Any]]:
    """
    Fetch the list of NSE circulars from the official API.
    Returns a list of circular metadata dicts.
    """
    with httpx.Client(headers=NSE_HEADERS, follow_redirects=True, timeout=30) as client:
        # Warm up: visit homepage inside the same context to obtain session cookies
        try:
            client.get(settings.nse_base_url)
            time.sleep(1)  # small delay to mimic human behaviour
        except httpx.HTTPError as exc:
            logger.warning("NSE homepage warm-up failed", error=str(exc))

        logger.info("Fetching NSE circulars", url=settings.nse_circulars_url)
        try:
            response = client.get(settings.nse_circulars_url)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "NSE API returned error",
                status=exc.response.status_code,
                url=settings.nse_circulars_url,
            )
            raise RuntimeError(
                f"NSE API error: HTTP {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            logger.error("NSE API request failed", error=str(exc))
            raise RuntimeError(f"NSE API request failed: {exc}") from exc

        data = response.json()

    # The API may return {"data": [...]} or a plain list
    if isinstance(data, dict):
        circulars = data.get("data", [])
    elif isinstance(data, list):
        circulars = data
    else:
        circulars = []

    logger.info("Fetched circulars", count=len(circulars))
    return circulars


def deduplicate(circulars: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Remove duplicate circulars based on circNumber within the fetched batch.
    Deduplication against MongoDB is handled separately.
    """
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for circ in circulars:
        key = circ.get("circNumber") or circ.get("circno") or ""
        if key and key not in seen:
            seen.add(key)
            unique.append(circ)
    logger.info("Deduplicated circulars", before=len(circulars), after=len(unique))
    return unique
