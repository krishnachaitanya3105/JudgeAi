"""
Timeline inference — relative phrases → deadline offset days and confidence.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

_REL_WEEKS_RE = re.compile(r"within\s+(\d+)\s*weeks?", re.IGNORECASE)
_REL_MONTHS_RE = re.compile(r"within\s+(\d+)\s*months?", re.IGNORECASE)
_REL_DAYS_RE = re.compile(r"within\s+(\d+)\s*days?", re.IGNORECASE)
_REASONABLE_RE = re.compile(r"within\s+(?:a\s+)?reasonable\s*time", re.IGNORECASE)
_IMMEDIATE_RE = re.compile(r"\b(?:immediately|forthwith)\b", re.IGNORECASE)


def extract_timeline_info(text: Optional[str], judgment_date: Optional[str]) -> Dict[str, Any]:
    """
    Parse relative timing phrases. Picks strongest known match.

    Returns:
      deadline_date, offset_days, confidence_score
    """
    text = text or ""
    base = _parse_anchor_date(judgment_date)
    lower = text.lower()

    candidates = []

    m = _REL_MONTHS_RE.search(lower)
    if m:
        n = int(m.group(1))
        candidates.append(("months", n * 30, 0.87))

    m = _REL_WEEKS_RE.search(lower)
    if m:
        n = int(m.group(1))
        candidates.append(("weeks", n * 7, 0.88))

    m = _REL_DAYS_RE.search(lower)
    if m:
        n = int(m.group(1))
        candidates.append(("days", n, 0.9))

    if _IMMEDIATE_RE.search(lower):
        candidates.append(("immediate", 3, 0.92))

    if _REASONABLE_RE.search(lower):
        candidates.append(("reasonable", 30, 0.55))

    if not candidates:
        return {
            "deadline_date": None,
            "offset_days": None,
            "confidence_score": 0.2,
            "matched": False,
        }

    # Prefer explicit smallest unit if multiple (days > weeks > months heuristic by confidence tie-break)
    candidates.sort(key=lambda x: (-x[2], x[1]))
    _, offset_days, conf = candidates[0]

    deadline_iso: Optional[str] = None
    if offset_days >= 0 and base:
        d = base + timedelta(days=offset_days)
        deadline_iso = d.date().isoformat()

    return {
        "deadline_date": deadline_iso,
        "offset_days": offset_days,
        "confidence_score": round(conf, 4),
        "matched": True,
    }


def _parse_anchor_date(judgment_date: Optional[str]) -> Optional[datetime]:
    if not judgment_date:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    jd = judgment_date.strip()[:10]
    try:
        return datetime.strptime(jd, "%Y-%m-%d")
    except ValueError:
        return datetime.now(timezone.utc).replace(tzinfo=None)
