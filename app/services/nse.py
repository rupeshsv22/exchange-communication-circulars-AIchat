from __future__ import annotations

import time
from typing import Any

import httpx

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Exact headers copied from browser DevTools / curl.
# Keep in sync with what NSE expects — update User-Agent / sec-ch-ua if blocked.
NSE_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9,en-IN;q=0.8",
    "dnt": "1",
    "priority": "u=1, i",
    "referer": "https://www.nseindia.com/resources/exchange-communication-circulars",
    "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Microsoft Edge";v="146"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0"
    ),
}


def _get_headers() -> dict[str, str]:
    """
    Build the final headers dict, injecting the Cookie from settings if set.
    Cookie is loaded from NSE_COOKIE in .env — update it there when it expires.
    """
    headers = dict(NSE_HEADERS)
    if settings.nse_cookie:
        headers["cookie"] = settings.nse_cookie
    return headers


def fetch_circulars() -> list[dict[str, Any]]:
    """
    Fetch the list of NSE circulars from the official API.
    Returns a list of circular metadata dicts.
    """
    headers = _get_headers()

    with httpx.Client(headers=headers, follow_redirects=True, timeout=30) as client:
        # If no cookie is configured, do a homepage warm-up to get session cookies
        if not settings.nse_cookie:
            try:
                client.get(settings.nse_base_url)
                time.sleep(1)
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
