"""
JudgeAI Configuration Module
──────────────────────────────────────────────────
Loads environment variables and provides a reusable
Supabase client instance for the entire application.
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# ── Load .env from project root ──────────────────
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ── Environment Variables ────────────────────────
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
SUPABASE_STORAGE_BUCKET: str = os.getenv("SUPABASE_STORAGE_BUCKET", "court-judgments")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

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
