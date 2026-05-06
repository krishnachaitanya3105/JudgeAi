"""
LLM Extractor Service — Groq LLaMA3.3-70B
──────────────────────────────────────────────────
Sends court judgment text to Groq's LLaMA model
and parses the structured JSON response.

Changes vs previous version:
  - max_chars default reduced to 12 000 (was 24 000) — halves request payload
    and significantly reduces Groq processing time on the free tier.
  - Accepts optional request_id for correlated logging.
  - Detailed per-attempt logging: attempt#, status code, elapsed.
  - 400 errors from Groq are now surfaced with the full body, not swallowed.
"""

import json
import logging
import os
import re
import time

import httpx

from backend.config import GROQ_API_KEY

logger = logging.getLogger("judgeai.llm_extractor")

# ── Groq API Configuration ──────────────────────
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_MODEL_ENV = "JUDGEAI_GROQ_MODEL"
GROQ_MAX_CHARS_ENV = "JUDGEAI_LLM_MAX_CHARS"
GROQ_MAX_TOKENS_ENV = "JUDGEAI_LLM_MAX_TOKENS"
GROQ_RETRIES_ENV = "JUDGEAI_LLM_RETRIES"
GROQ_TIMEOUT_ENV = "JUDGEAI_LLM_TIMEOUT_SEC"

# ── System Prompt ─────────────────────────────────
SYSTEM_PROMPT = """You are a legal governance assistant.

Your task is to carefully analyze the provided court judgment text and extract the following fields:

1. **case_number** — The official case/filing number.
2. **judgment_date** — The date the judgment was issued (ISO 8601 format: YYYY-MM-DD).
3. **department** — The responsible government department or authority.
4. **deadline** — The **specific calendar date** by which compliance must be complete, as **YYYY-MM-DD only**.
   If only a relative period is given (e.g. \"within 30 days\"), convert it to an absolute date **using judgment_date** when you can; if you cannot compute a calendar date, use **null**. Never return phrases like \"30 days from\" in this field.
5. **directive** — The specific directive, action, or order required.
6. **confidence_score** — A float between 0.0 and 1.0 indicating your confidence in the extraction accuracy.
7. **source_sentence** — The exact sentence from judgment text that best supports the directive extraction.

RULES:
- Return ONLY valid JSON. No markdown, no explanation, no extra text.
- If a field cannot be determined, use null.
- The response must be a single JSON object (not an array).

Example output:
{
  "case_number": "WP(C) 12345/2024",
  "judgment_date": "2024-03-15",
  "department": "Ministry of Environment",
  "deadline": "2024-06-15",
  "directive": "Submit compliance report within 90 days",
  "confidence_score": 0.85,
  "source_sentence": "The respondent ministry shall submit the compliance report within 90 days."
}"""


def _parse_json_response(raw_text: str) -> dict:
    """
    Robustly parse JSON from LLM output.
    Handles markdown code fences and partial JSON.
    """
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not parse JSON from LLM response: {raw_text[:200]}")


def extract_judgment_actions(
    judgment_text: str,
    request_id: str = "n/a",
) -> dict:
    """
    Send court judgment text to Groq and return structured extraction dict.

    Args:
        judgment_text: Raw text extracted from a court judgment PDF.
        request_id:    Correlation ID for log tracing.

    Returns:
        Dict with keys: case_number, judgment_date, department,
        deadline, directive, confidence_score, source_sentence.

    Raises:
        ValueError: If the LLM response cannot be parsed or the API errors.
    """
    max_chars = int(os.getenv(GROQ_MAX_CHARS_ENV, "12000"))   # reduced default
    if len(judgment_text) > max_chars:
        judgment_text = judgment_text[:max_chars] + "\n\n[...truncated...]"

    model = os.getenv(GROQ_MODEL_ENV, GROQ_MODEL)
    max_tokens = int(os.getenv(GROQ_MAX_TOKENS_ENV, "1024"))
    retries = int(os.getenv(GROQ_RETRIES_ENV, "2"))
    timeout_sec = float(os.getenv(GROQ_TIMEOUT_ENV, "60"))

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Extract the required fields from the following court judgment:\n\n"
                    f"{judgment_text}"
                ),
            },
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    logger.info(
        "[llm_extractor] req=%s model=%s chars=%d timeout=%.0fs",
        request_id, model, len(judgment_text), timeout_sec,
    )

    last_err = None
    response = None
    with httpx.Client(timeout=timeout_sec) as client:
        for attempt in range(retries + 1):
            t0 = time.monotonic()
            try:
                response = client.post(GROQ_API_URL, json=payload, headers=headers)
                elapsed = time.monotonic() - t0
                logger.info(
                    "[llm_extractor] req=%s attempt=%d status=%d elapsed=%.2fs",
                    request_id, attempt + 1, response.status_code, elapsed,
                )
                response.raise_for_status()
                break
            except httpx.HTTPStatusError as e:
                elapsed = time.monotonic() - t0
                last_err = e
                code = e.response.status_code
                body = e.response.text[:300]
                logger.warning(
                    "[llm_extractor] req=%s attempt=%d HTTP %d in %.2fs body=%s",
                    request_id, attempt + 1, code, elapsed, body,
                )
                # Retry on transient errors; 400 is a bad-request (model/payload issue) — no retry
                retryable = {408, 409, 425, 429, 500, 502, 503, 504}
                if attempt < retries and code in retryable:
                    wait = 0.6 * (2 ** attempt)
                    logger.info("[llm_extractor] req=%s retrying in %.1fs…", request_id, wait)
                    time.sleep(wait)
                    continue
                raise ValueError(
                    f"Groq API error {code}: {body}"
                ) from e
            except (httpx.TimeoutException, httpx.TransportError) as e:
                elapsed = time.monotonic() - t0
                last_err = e
                logger.warning(
                    "[llm_extractor] req=%s attempt=%d network error in %.2fs: %s",
                    request_id, attempt + 1, elapsed, str(e)[:120],
                )
                if attempt < retries:
                    wait = 0.6 * (2 ** attempt)
                    time.sleep(wait)
                    continue
                raise ValueError(f"Groq API request failed (network): {e}") from e
        else:
            raise ValueError(f"Groq API request failed after {retries + 1} attempts: {last_err}")

    data = response.json()
    raw_content = data["choices"][0]["message"]["content"]
    parsed = _parse_json_response(raw_content)
    parsed.setdefault("source_sentence", None)
    parsed.setdefault("confidence_score", 0.0)

    logger.info(
        "[llm_extractor] req=%s parsed OK case=%s conf=%s",
        request_id, parsed.get("case_number"), parsed.get("confidence_score"),
    )
    return parsed
