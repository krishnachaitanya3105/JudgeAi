"""
JudgeAI Utility Helpers
──────────────────────────────────────────────────
Common helper functions used across the application.
"""

import re
import uuid
from datetime import datetime, timezone


def generate_case_id(prefix: str = "CASE") -> str:
    """Generate a unique case identifier."""
    short_id = uuid.uuid4().hex[:10].upper()
    return f"{prefix}-{short_id}"


def sanitize_filename(filename: str) -> str:
    """Remove unsafe characters from a filename."""
    return re.sub(r"[^\w\-.]", "_", filename)


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def truncate_text(text: str, max_length: int = 24_000) -> str:
    """Truncate text to fit within LLM context limits."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "\n\n[...truncated...]"


def clean_extracted_text(text: str) -> str:
    """
    Clean up text extracted from PDFs:
    - Collapse multiple whitespace
    - Remove null bytes
    - Strip leading/trailing whitespace
    """
    text = text.replace("\x00", "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()
