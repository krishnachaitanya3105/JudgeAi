"""
Appeal recommendation from judgment text cues.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional


_LIBERTY_RE = re.compile(r"liberty\s+to\s+appeal", re.IGNORECASE)
_PARTLY_ALLOWED_RE = re.compile(r"partly\s+allowed", re.IGNORECASE)
_PETITION_ALLOWED_RE = re.compile(r"petition\s+allowed(?!\s+in\s+part)", re.IGNORECASE)
_DISMISSED_RE = re.compile(r"petition\s+dismissed|writ\s+dismissed", re.IGNORECASE)
_STAY_RE = re.compile(r"stay\s+granted|stay\s+(?:is\s+)?continued?", re.IGNORECASE)
_INTERIM_RE = re.compile(r"interim\s+order", re.IGNORECASE)
_DISPOSED_RE = re.compile(r"disposed\s+of\b", re.IGNORECASE)
_SERVICE_HINT_RE = re.compile(
    r"service\s+law|employment|termination|departmental\s+(?:enquiry|proceeding)|disciplinary",
    re.IGNORECASE,
)


def recommend_appeal(judgment_text: Optional[str], matter_type_hint: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns appeal_recommended, confidence_score, limitation_period_days.

    Defaults: civil → 90 days, service-related → 30 days.
    """
    raw = judgment_text or ""
    text = raw.lower()

    limitation = 30 if _SERVICE_HINT_RE.search(raw) or (matter_type_hint and "service" in matter_type_hint.lower()) else 90

    appeal_rec = ""
    conf = 0.4

    if _DISMISSED_RE.search(text):
        appeal_rec = "NO"
        conf = 0.82

    if _PETITION_ALLOWED_RE.search(text):
        appeal_rec = "YES"
        conf = max(conf, 0.78)

    if _LIBERTY_RE.search(text) or _PARTLY_ALLOWED_RE.search(text):
        appeal_rec = "YES"
        conf = max(conf, 0.85)

    if _STAY_RE.search(text) or _INTERIM_RE.search(text):
        if appeal_rec not in {"YES"}:
            appeal_rec = "REVIEW"
        conf = max(conf, 0.72)

    if _DISPOSED_RE.search(text) and appeal_rec not in {"YES", "NO"}:
        appeal_rec = "REVIEW"
        conf = max(conf, 0.55)

    return {
        "appeal_recommended": appeal_rec,
        "confidence_score": round(min(conf, 1.0), 4),
        "limitation_period_days": limitation,
    }
