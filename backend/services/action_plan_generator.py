"""
Structured government action plan from extracted judgment fields + engines.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from backend.services.appeal_recommender import recommend_appeal
from backend.services.confidence_fusion import summarize_fusion_inputs
from backend.services.department_classifier import pick_department
from backend.services.timeline_parser import extract_timeline_info

_COMPLIANCE_PAT = re.compile(
    r"reinstate|release\s+payment|implement\s+(?:order|the\s+order)|"
    r"comply|compliance|deposit\s+|pay\s+|execute\s+(?:order|direction)",
    re.IGNORECASE,
)
_DISMISS_PAT = re.compile(r"petition\s+dismissed|writ\s+dismissed", re.IGNORECASE)
_APPEAL_REVIEW_PAT = re.compile(
    r"partly\s+allowed|liberty\s+to\s+appeal|leave\s+to\s+appeal",
    re.IGNORECASE,
)


def _directive_action_kind(directive: str) -> str:
    d = directive or ""
    if _DISMISS_PAT.search(d):
        return "NO_ACTION_REQUIRED"
    if _APPEAL_REVIEW_PAT.search(d):
        return "REVIEW_FOR_APPEAL"
    if _COMPLIANCE_PAT.search(d):
        return "COMPLIANCE_REQUIRED"
    return "ADMINISTRATIVE_REVIEW"


def _priority_level_from_deadline(deadline_iso: Optional[str]) -> str:
    if not deadline_iso:
        return "LOW"
    try:
        d = deadline_iso[:10]
        dd = datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days = (dd - now).days
        if days < 0:
            return "HIGH"
        if days < 7:
            return "HIGH"
        if days < 30:
            return "MEDIUM"
        return "LOW"
    except ValueError:
        return "LOW"


def generate_action_plan(
    extracted_action: dict,
    full_judgment_text: Optional[str] = None,
    timeline_hint_text: Optional[str] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Returns:
      flat action_plan matching prompt schema
      reasoning payload for action_plan_reasoning column (+ fusion breakdown)
    """
    directive = extracted_action.get("directive") or ""
    dept_llm = extracted_action.get("department")
    jd = extracted_action.get("judgment_date")
    llm_deadline = extracted_action.get("deadline")
    case_no = extracted_action.get("case_number") or ""
    llm_conf = float(extracted_action.get("confidence_score") or 0.0)
    excerpt = extracted_action.get("source_sentence") or directive
    full_text = full_judgment_text or excerpt or directive

    text_for_timeline = " ".join(
        filter(
            None,
            [
                directive,
                extracted_action.get("source_sentence"),
                timeline_hint_text,
            ],
        )
    )

    timeline = extract_timeline_info(text_for_timeline, jd)
    dept_pick = pick_department(dept_llm, full_text[:12000])
    appeal = recommend_appeal(full_text)

    kind = _directive_action_kind(directive)
    if appeal.get("appeal_recommended") == "YES" and kind != "NO_ACTION_REQUIRED":
        action_type = "REVIEW_FOR_APPEAL"
    elif kind == "COMPLIANCE_REQUIRED":
        action_type = "COMPLIANCE_REQUIRED"
    elif kind == "NO_ACTION_REQUIRED":
        action_type = "NO_ACTION_REQUIRED"
    elif kind == "REVIEW_FOR_APPEAL":
        action_type = "REVIEW_FOR_APPEAL"
    else:
        action_type = "ADMINISTRATIVE_REVIEW"

    compliance_deadline = llm_deadline or timeline.get("deadline_date")
    appeal_lim = appeal.get("limitation_period_days") or 90
    appeal_deadline = ""
    if appeal.get("appeal_recommended") == "YES" and jd:
        try:
            base = datetime.strptime(str(jd)[:10], "%Y-%m-%d")
            appeal_deadline = (base + timedelta(days=int(appeal_lim))).date().isoformat()
        except (ValueError, TypeError):
            appeal_deadline = ""

    fused = summarize_fusion_inputs(
        llm_conf,
        timeline.get("confidence_score"),
        dept_pick.get("classifier_confidence"),
        appeal.get("confidence_score"),
    )
    prio = _priority_level_from_deadline(compliance_deadline if isinstance(compliance_deadline, str) else None)
    fused_score = fused["final_action_plan_confidence"]

    action_plan = {
        "case_number": case_no,
        "department": dept_pick.get("department") or "",
        "action_required": directive or "",
        "action_type": action_type,
        "priority_level": prio,
        "appeal_recommended": appeal.get("appeal_recommended") or "",
        "appeal_deadline": appeal_deadline,
        "compliance_deadline": str(compliance_deadline or "")[:10] if compliance_deadline else "",
        "responsible_officer_role": "Nodal Officer / Department Head",
        "confidence_score": round(float(fused_score), 6),
    }

    reasoning = {
        **fused,
        "why_appeal_recommended": (
            f"Classifier appeal flag={appeal.get('appeal_recommended')} (conf={appeal.get('confidence_score')}); "
            f"limitation baseline {appeal_lim} days from judgment anchor."
        ),
        "why_department_selected": (
            f"Embedding classifier suggested {dept_pick.get('classifier_raw_department')} "
            f"(conf={dept_pick.get('classifier_confidence')}); LLM hinted {dept_pick.get('llm_department')}; "
            f"{'overrode LLM' if dept_pick.get('overridden') else 'kept LLM / heuristic merge'}."
        ),
        "why_deadline_inferred": (
            f"Timeline NLP: matched={timeline.get('matched')} offset_days={timeline.get('offset_days')} "
            f"(conf={timeline.get('confidence_score')}); fallback LLM deadline={llm_deadline}."
        ),
        "timeline_detail": timeline,
        "department_detail": dept_pick,
        "appeal_detail": appeal,
    }

    return action_plan, reasoning
