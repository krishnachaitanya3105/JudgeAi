"""
Coerce arbitrary LLM / narrative date strings to YYYY-MM-DD for PostgreSQL DATE columns.

If text is purely relative (no calendar date digits), returns None so inserts stay valid.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional

_ISO_ANYWHERE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_RELATIVE_WITHOUT_DATE = re.compile(
    r"^(?=.*\b(?:within|about|around|forthwith|days?|weeks?|months?)\b)(?!.*\d{4}-\d{2}-\d{2}).*$",
    re.IGNORECASE | re.DOTALL,
)
_DMY = re.compile(r"^(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\b")


def coerce_pg_date(value: Any) -> Optional[str]:
    """
    Return YYYY-MM-DD safe for Postgres DATE, or None if not a concrete calendar date.
    Accepts embedded ISO dates (first valid wins), e.g. \"on or before 2024-04-29\".
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return None
    raw = str(value).strip().strip('"').strip("'")
    if not raw or raw.lower() in {"null", "none", "n/a", "na", "--"}:
        return None

    # Pure-relative garbage like "30 days fr" → no digit triplet anywhere
    if _RELATIVE_WITHOUT_DATE.match(raw.strip()) or (
        ("day" in raw.lower() or "week" in raw.lower())
        and not _ISO_ANYWHERE.search(raw)
        and not _DMY.match(raw.strip())
    ):
        return None

    for m in _ISO_ANYWHERE.finditer(raw):
        cand = m.group(1)
        try:
            datetime.strptime(cand, "%Y-%m-%d")
            return cand
        except ValueError:
            continue

    dmy = _DMY.match(raw.strip())
    if dmy:
        d, mo, y = int(dmy.group(1)), int(dmy.group(2)), int(dmy.group(3))
        try:
            return datetime(y, mo, d).date().isoformat()
        except ValueError:
            pass

    sample = raw[:48].strip()
    for fmt in ("%Y-%m-%d", "%d %B %Y", "%d %b %Y", "%B %d, %Y", "%b %d, %Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(sample, fmt).date().isoformat()
        except ValueError:
            continue

    return None


def sanitize_action_plan_date_fields(plan: dict) -> None:
    """Mutate action_plan strings to ISO-only or \"\" for deadline-like keys."""
    if not isinstance(plan, dict):
        return
    for key in ("compliance_deadline", "appeal_deadline"):
        if key not in plan:
            continue
        coerced = coerce_pg_date(plan[key])
        plan[key] = coerced if coerced else ""
