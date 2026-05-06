"""
LLM Extractor Service — Groq LLaMA3.3-70B
──────────────────────────────────────────────────
Sends court judgment text to Groq's LLaMA model
and parses the structured JSON response containing:
  - case_number
  - judgment_date
  - department
  - deadline
  - directive
  - confidence_score
  - source_sentence

✅ FIXED: Updated model from deprecated llama-3.1-8b-instant to llama-3.3-70b-versatile
   The error "400 Bad Request" with the old model was because many Groq models have been
   decommissioned. The llama-3.3-70b-versatile is the current active model.
"""

import json
import os
import re
import time
import httpx

from backend.config import GROQ_API_KEY

# ── Groq API Configuration ──────────────────────
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"  # Default; override via env when needed
GROQ_MODEL_ENV = "JUDGEAI_GROQ_MODEL"
GROQ_MAX_CHARS_ENV = "JUDGEAI_LLM_MAX_CHARS"
GROQ_MAX_TOKENS_ENV = "JUDGEAI_LLM_MAX_TOKENS"
GROQ_RETRIES_ENV = "JUDGEAI_LLM_RETRIES"
GROQ_TIMEOUT_ENV = "JUDGEAI_LLM_TIMEOUT_SEC"

# ── System Prompt ────────────────────────────────
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
    Handles cases where the model wraps JSON in markdown code blocks.
    """
    # Strip markdown code fences if present
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Attempt to find JSON object in the text
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not parse JSON from LLM response: {raw_text[:200]}")


def extract_judgment_actions(judgment_text: str) -> dict:
    """
    Send court judgment text to Groq LLaMA3-8B and return
    structured extraction as a Python dict.

    Args:
        judgment_text: Raw text extracted from a court judgment PDF.

    Returns:
        Dict with keys: case_number, judgment_date, department,
        deadline, directive, confidence_score, source_sentence.

    Raises:
        ValueError: If the LLM response cannot be parsed as JSON.
        httpx.HTTPStatusError: If the Groq API returns an error.
    """
    # Truncate very long texts to stay within context window
    max_chars = int(os.getenv(GROQ_MAX_CHARS_ENV, "24000"))
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

    last_err = None
    with httpx.Client(timeout=timeout_sec) as client:
        for attempt in range(retries + 1):
            try:
                response = client.post(GROQ_API_URL, json=payload, headers=headers)
                response.raise_for_status()
                break
            except httpx.HTTPStatusError as e:
                last_err = e
                code = e.response.status_code
                # Retry on rate-limit / transient backend failures.
                if attempt < retries and code in {408, 409, 425, 429, 500, 502, 503, 504}:
                    time.sleep(0.6 * (2**attempt))
                    continue
                error_body = e.response.text
                raise ValueError(f"Groq API error {code}: {error_body}")
            except (httpx.TimeoutException, httpx.TransportError) as e:
                last_err = e
                if attempt < retries:
                    time.sleep(0.6 * (2**attempt))
                    continue
                raise ValueError(f"Groq API request failed: {str(e)}")
        else:
            raise ValueError(f"Groq API request failed: {str(last_err)}")

    data = response.json()
    raw_content = data["choices"][0]["message"]["content"]

    parsed = _parse_json_response(raw_content)
    parsed.setdefault("source_sentence", None)
    parsed.setdefault("confidence_score", 0.0)
    return parsed
