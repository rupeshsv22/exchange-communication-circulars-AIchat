from __future__ import annotations

import io
import time
import zipfile
from typing import Any

import httpx
from pypdf import PdfReader

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ZIP magic bytes: PK\x03\x04
_ZIP_MAGIC = b"PK\x03\x04"

NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,application/zip,*/*",
    "Referer": "https://www.nseindia.com/",
}


def build_pdf_url(file_link: str) -> str:
    """
    Ensure the PDF URL is absolute.
    NSE sometimes returns relative paths like /content/circulars/foo.pdf
    """
    if file_link.startswith("http"):
        return file_link
    return settings.nse_base_url + file_link


_MAX_RETRIES = 3
_RETRY_BACKOFF = [2, 5, 10]  # seconds to wait before each retry attempt


def download_pdf(file_link: str) -> bytes | None:
    """
    Download a PDF/ZIP by its link with up to _MAX_RETRIES retries.
    Retries on transient network errors (DNS failure, connection reset, timeout).
    Returns raw bytes or None if all attempts fail.
    """
    url = build_pdf_url(file_link)

    # Determine archive host for warm-up (may differ from nseindia.com)
    from urllib.parse import urlparse
    parsed = urlparse(url)
    archive_origin = f"{parsed.scheme}://{parsed.netloc}"

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            with httpx.Client(headers=NSE_HEADERS, follow_redirects=True, timeout=60) as client:
                # Warm up the specific host to get session cookies
                try:
                    client.get(settings.nse_base_url)
                    if archive_origin != settings.nse_base_url:
                        client.get(archive_origin)
                    time.sleep(0.5)
                except httpx.HTTPError:
                    pass  # warm-up failure is non-fatal

                response = client.get(url)
                response.raise_for_status()
                logger.info(
                    "Downloaded file",
                    url=url,
                    size_bytes=len(response.content),
                    attempt=attempt,
                )
                return response.content

        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            # Transient: DNS failure, connection reset, timeout → retry
            wait = _RETRY_BACKOFF[attempt - 1]
            logger.warning(
                "Transient download error, retrying",
                url=url,
                attempt=attempt,
                max=_MAX_RETRIES,
                wait_s=wait,
                error=str(exc),
            )
            if attempt < _MAX_RETRIES:
                time.sleep(wait)

        except httpx.HTTPStatusError as exc:
            # Non-retriable HTTP error (4xx/5xx)
            logger.warning(
                "Failed to download file (HTTP error)",
                url=url,
                status=exc.response.status_code,
            )
            return None

    logger.warning("All download attempts failed", url=url, attempts=_MAX_RETRIES)
    return None


def _unwrap_zip(data: bytes) -> bytes | None:
    """
    If `data` is a ZIP archive, extract and return the first PDF found inside.
    Returns None if no PDF entry exists in the archive.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            pdf_names = [n for n in zf.namelist() if n.lower().endswith(".pdf")]
            if not pdf_names:
                logger.warning("ZIP contains no PDF entries", entries=zf.namelist())
                return None
            # Take the first PDF (most circulars contain exactly one)
            pdf_name = pdf_names[0]
            logger.info("Extracting PDF from ZIP", entry=pdf_name)
            return zf.read(pdf_name)
    except zipfile.BadZipFile as exc:
        logger.warning("Not a valid ZIP file", error=str(exc))
        return None


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract all text from PDF bytes (or a ZIP wrapping a PDF).
    Empty pages are skipped gracefully.
    Returns the combined text string.
    """
    # Transparently handle ZIP-wrapped PDFs (NSE archive format)
    if pdf_bytes[:4] == _ZIP_MAGIC:
        logger.info("Detected ZIP archive; unwrapping PDF")
        pdf_bytes = _unwrap_zip(pdf_bytes) or b""
        if not pdf_bytes:
            return ""

    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
    except Exception as exc:
        logger.warning("Could not parse PDF", error=str(exc))
        return ""

    pages_text: list[str] = []
    for page_num, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
            text = text.strip()
            if text:
                pages_text.append(text)
        except Exception as exc:
            logger.warning("Could not extract page text", page=page_num, error=str(exc))

    combined = "\n".join(pages_text)
    logger.info("Extracted PDF text", pages=len(reader.pages), chars=len(combined))
    return combined


def process_circular_pdf(circular: dict[str, Any]) -> str:
    """
    Download and extract text from the PDF linked in a circular dict.
    Returns extracted text, or empty string on any failure.
    """
    file_link: str = circular.get("circFilelink") or circular.get("filelink") or ""
    if not file_link:
        logger.warning("No file link in circular", circ_number=circular.get("circNumber"))
        return ""

    pdf_bytes = download_pdf(file_link)
    if not pdf_bytes:
        return ""

    return extract_text_from_pdf(pdf_bytes)
