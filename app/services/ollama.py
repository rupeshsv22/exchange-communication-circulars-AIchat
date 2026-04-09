from __future__ import annotations

import httpx

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Used for general topic queries — brief bullet-point answer
BRIEF_PROMPT = """\
You are a financial assistant specialized in NSE circulars. Answer ONLY from the context below.

STRICT OUTPUT FORMAT — follow exactly:
• <one-line finding> [NSE({{circNumber}})]
• <one-line finding> [NSE({{circNumber}})]
(2-3 bullets max, no extra text, no summaries, no introductions)

If the answer is not in the context, output exactly: No relevant circular found

Example of correct output:
• ST-ASM surveillance measure applied to XYZ Ltd shares [NSE(73500)]
• Trading shifted from BE to EQ series for ABC Ltd [NSE(73488)]

Context:
{context}

Question: {question}
Answer:"""

# Used when a specific circular number is requested — full structured details
DETAIL_PROMPT = """\
You are a financial assistant specialized in NSE circulars. Answer ONLY from the context below.

Present the complete details of the circular in this structure:
Circular No   : <circNumber>
Ref No        : <reference number if present>
Date          : <date>
Department    : <department>
Subject       : <subject>
Details       : <full body — include all schemes, ISINs, dates, deadlines, and instructions>
Issued By     : <signatory names and designations if present>
Source        : NSE(<circNumber>)

If information for a field is not in the context, write "N/A" for that field.
If the circular is not in the context, output exactly: No relevant circular found

Context:
{context}

Question: {question}
Answer:"""


def build_prompt(context: str, question: str, detail_mode: bool = False) -> str:
    template = DETAIL_PROMPT if detail_mode else BRIEF_PROMPT
    return template.format(context=context, question=question)


def query_ollama(prompt: str) -> str:
    """
    Send a prompt to the local Ollama API and return the model's response text.
    Raises RuntimeError on failure.
    """
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
    }
    url = f"{settings.ollama_base_url}/api/generate"

    try:
        with httpx.Client(timeout=180) as client:
            logger.info(
                "Calling Ollama",
                model=settings.ollama_model,
                prompt_chars=len(prompt),
                url=url,
            )
            response = client.post(url, json=payload)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        # Log the actual Ollama error body so we can diagnose it
        body = exc.response.text[:500]
        logger.error(
            "Ollama returned error",
            status=exc.response.status_code,
            body=body,
        )
        raise RuntimeError(
            f"Ollama error: HTTP {exc.response.status_code} — {body}"
        ) from exc
    except httpx.HTTPError as exc:
        logger.error("Ollama request failed", error=str(exc))
        raise RuntimeError(f"Ollama unavailable: {exc}") from exc

    data = response.json()
    answer: str = data.get("response", "").strip()
    logger.info("Ollama responded", chars=len(answer))
    return answer
