"""
Highlights for react-pdf-highlighter from layout blocks + extraction fields.

Priority per block (first match wins): party (green) → deadline (blue) → directive (yellow).
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional, Set

_ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_DATEISH = re.compile(
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\bwithin\s+\d+\s*(?:days?|weeks?|months?)\b|\bforthwith\b|\bimmediately\b",
    re.IGNORECASE,
)
_PARTY_LABEL = re.compile(
    r"\b(?:petitioner|respondent|appellant|opposite\s+party|writ\s+petitioner)s?\s*[:\u2014\-]",
    re.IGNORECASE,
)


def _collect_deadline_hints(
    deadline: Optional[str],
    compliance: Optional[str],
    appeal_deadline: Optional[str],
    judgment_date: Optional[str],
) -> Set[str]:
    hints: Set[str] = set()
    for blob in (deadline, compliance, appeal_deadline, judgment_date):
        if not blob:
            continue
        s = str(blob)
        hints.update(_ISO.findall(s))
        if len(s) <= 40 and len(s.strip()) >= 8:
            hints.add(s.strip().lower()[:36])
    return hints


def _directive_tokens(directive: Optional[str], source_sentence: Optional[str]) -> List[str]:
    text = " ".join(filter(None, [directive or "", (source_sentence or "")[:900]]))
    tokens = sorted({w.lower() for w in re.split(r"\W+", text) if len(w) >= 5}, key=len, reverse=True)
    return tokens[:42]


def _party_name_hints(directive: Optional[str], source_sentence: Optional[str]) -> List[str]:
    blobs = []
    for para in filter(None, [directive, source_sentence]):
        for m in re.finditer(
            r"(?i)(petitioner|respondent|appellant)\s*[:\u2014\-]\s*([^\.\n\r]{4,140})",
            para,
        ):
            frag = (m.group(2) or "").strip()
            chunks = [
                frag[: min(72, len(frag))],
                frag.split(",")[0].strip()[:64] if frag else "",
            ]
            blobs.extend(chunks)
        for m in re.finditer(r"(?i)\bversus\b\s+([\w\s,''-]{6,140})", para):
            blobs.append(m.group(1).strip()[:100])
    out = sorted({s.lower().strip() for s in blobs if len(s.strip()) >= 4}, key=len, reverse=True)
    return out[:22]


def _scaled_rect(page_number: int, bbox: List[float]) -> Dict[str, Any]:
    if not bbox or len(bbox) < 4:
        return {}
    x0, y0, x1, y1 = bbox[0], bbox[1], bbox[2], bbox[3]
    return {
        "left": float(x0),
        "top": float(y0),
        "width": float(x1 - x0),
        "height": float(y1 - y0),
        "pageNumber": page_number,
    }


def layout_blocks_to_highlights(
    layout_blocks: Optional[List[Dict[str, Any]]],
    directive: Optional[str],
    deadline: Optional[str],
    *,
    source_sentence: Optional[str] = None,
    judgment_date_iso: Optional[str] = None,
    compliance_deadline: Optional[str] = None,
    appeal_deadline: Optional[str] = None,
) -> List[Dict[str, Any]]:
    blocks = layout_blocks or []
    if not blocks:
        return []

    dnorm = (directive or "").strip().lower()[:520]
    d_prefixes = []
    step = max(36, len(dnorm) // 5 or 36)
    for i in range(0, len(dnorm), step // 2):
        frag = dnorm[i : i + 72].strip()
        if len(frag) >= 12:
            d_prefixes.append(frag)

    directive_words = _directive_tokens(directive, source_sentence)
    party_hints = _party_name_hints(directive, source_sentence)

    dhints = _collect_deadline_hints(
        deadline,
        compliance_deadline,
        appeal_deadline,
        judgment_date_iso,
    )

    highlights: List[Dict[str, Any]] = []

    for blk in blocks:
        text = (blk.get("text") or "").strip()
        if len(text) < 3:
            continue
        bbox = blk.get("bbox")
        pn = int(blk.get("page_number") or 1)
        tlow = text.lower()

        hl_type = ""

        if _PARTY_LABEL.search(text):
            hl_type = "party"
        else:
            for ph in party_hints:
                if ph and ph in tlow:
                    hl_type = "party"
                    break

        if not hl_type:
            for iso in dhints:
                if re.match(r"^\d{4}-\d{2}-\d{2}$", iso) and iso in text:
                    hl_type = "deadline"
                    break
            if not hl_type and _ISO.search(text):
                hl_type = "deadline"
            if not hl_type and dhints:
                for h in dhints:
                    if len(h) >= 8 and h in tlow:
                        hl_type = "deadline"
                        break
            if not hl_type and deadline and str(deadline).lower()[:40] and str(deadline).lower() in tlow:
                hl_type = "deadline"
            if not hl_type and (_DATEISH.search(text) or _ISO.search(text)):
                hl_type = "deadline"

        if not hl_type:
            for pf in d_prefixes:
                if pf and pf in tlow:
                    hl_type = "directive"
                    break
            if not hl_type:
                hits = sum(1 for w in directive_words[:18] if w in tlow)
                if hits >= 2:
                    hl_type = "directive"
                elif len(directive_words) <= 12 and directive_words:
                    wl = directive_words[0]
                    if len(wl) >= 6 and wl in tlow:
                        hl_type = "directive"

        if not hl_type:
            continue

        rect = _scaled_rect(pn, bbox if bbox else [])
        if not rect:
            continue

        emoji = {"directive": "🟨", "deadline": "🟦", "party": "🟩"}.get(hl_type, "")

        highlights.append(
            {
                "id": str(uuid.uuid4()),
                "position": {
                    "boundingRect": rect,
                    "rects": [rect],
                    "pageNumber": pn,
                    "usePdfCoordinates": True,
                },
                "content": {"text": text[:280]},
                "comment": {"text": hl_type.upper(), "emoji": emoji},
            }
        )

    return highlights[:48]
