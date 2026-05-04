"""Single SentenceTransformer (MiniLM) for embedding + department classification — avoids double model load."""

from __future__ import annotations

_encoder = None


def get_minilm_encoder():
    """Lazy-loaded shared model (~one load instead of two per request)."""
    global _encoder
    if _encoder is None:
        from sentence_transformers import SentenceTransformer

        _encoder = SentenceTransformer("all-MiniLM-L6-v2")
    return _encoder
