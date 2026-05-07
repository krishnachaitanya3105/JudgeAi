"""
JudgeAI Configuration Module
──────────────────────────────────────────────────
Loads environment variables and provides a reusable
Supabase client instance for the entire application.
"""

import os
import httpx
from contextlib import contextmanager
from dotenv import load_dotenv
from supabase import create_client, Client

# ── Load .env from project root ──────────────────
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ── Environment Variables ────────────────────────
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
SUPABASE_STORAGE_BUCKET: str = os.getenv("SUPABASE_STORAGE_BUCKET", "court-judgments")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

# ── HTTP Request Timeouts (in seconds) ───────────
DEFAULT_REQUEST_TIMEOUT = float(os.getenv("DEFAULT_REQUEST_TIMEOUT_SEC", "30"))
PDF_REQUEST_TIMEOUT = float(os.getenv("JUDGEAI_PDF_REQUEST_TIMEOUT_SEC", "45"))
LLM_REQUEST_TIMEOUT = float(os.getenv("JUDGEAI_LLM_TIMEOUT_SEC", "55"))

# ── Validation ───────────────────────────────────
_required = {
    "SUPABASE_URL": SUPABASE_URL,
    "SUPABASE_KEY": SUPABASE_KEY,
    "GROQ_API_KEY": GROQ_API_KEY,
}

for name, value in _required.items():
    if not value:
        raise EnvironmentError(f"Missing required environment variable: {name}")

# ── Reusable Supabase Client ────────────────────
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_supabase() -> Client:
    """Return the singleton Supabase client."""
    return supabase


@contextmanager
def get_httpx_client(timeout: float = DEFAULT_REQUEST_TIMEOUT):
    """
    Context manager for creating httpx clients with proper timeout.
    Usage:
        with get_httpx_client() as client:
            response = client.get(url)
    """
    client = httpx.Client(timeout=timeout)
    try:
        yield client
    finally:
        client.close()
