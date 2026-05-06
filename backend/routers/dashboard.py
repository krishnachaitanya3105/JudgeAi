"""
Dashboard Router — Officer and Admin Dashboards
──────────────────────────────────────────────────
Government decision widgets + case filters over action_plan payloads.
"""

import asyncio
from datetime import datetime, timedelta, timezone
import logging
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.config import get_supabase
from backend.services.confidence_fusion import NEUTRAL_IMPUTATION, default_fusion_weights
from backend.services.highlight_builder import layout_blocks_to_highlights
from backend.utils.deadline_helper import calculate_deadline_remaining, is_deadline_imminent

logger = logging.getLogger("judgeai.dashboard")
router = APIRouter()


def _action_snapshot(action: dict) -> dict:
    ap = action.get("action_plan") or {}
    return {
        "id": action.get("id"),
        "case_number": action.get("case_number"),
        "department": ap.get("department") or action.get("department"),
        "directive": (action.get("directive") or "")[:280],
        "deadline": ap.get("compliance_deadline") or action.get("deadline"),
        "priority_level": ap.get("priority_level"),
        "action_type": ap.get("action_type"),
        "appeal_recommended": ap.get("appeal_recommended"),
        "status": action.get("status"),
    }


def government_dashboard_slices(actions: list) -> dict:
    appeal_cases: List[dict] = []
    compliance_cases: List[dict] = []
    upcoming_7: List[dict] = []
    dept_pending: dict = {}

    seen_appeal = set()
    seen_compliance = set()
    seen_upcoming = set()

    for action in actions:
        ap = action.get("action_plan") or {}
        card = _action_snapshot(action)
        case_num = action.get("case_number")

        ar = str(ap.get("appeal_recommended", "")).strip().upper()
        if ar in {"YES", "REVIEW"} and len(appeal_cases) < 50 and case_num not in seen_appeal:
            appeal_cases.append(card)
            seen_appeal.add(case_num)

        if ap.get("action_type") == "COMPLIANCE_REQUIRED" and len(compliance_cases) < 50 and case_num not in seen_compliance:
            compliance_cases.append(card)
            seen_compliance.add(case_num)

        dl_raw = ap.get("compliance_deadline") or action.get("deadline")
        if dl_raw and case_num not in seen_upcoming:
            info = calculate_deadline_remaining(str(dl_raw))
            dr = info.get("days_remaining")
            if dr is not None and 0 <= dr <= 7 and len(upcoming_7) < 50:
                row = dict(card)
                row["days_remaining"] = dr
                upcoming_7.append(row)
                seen_upcoming.add(case_num)

        if action.get("status") == "pending":
            dk = str(ap.get("department") or action.get("department") or "Unknown")
            dept_pending[dk] = dept_pending.get(dk, 0) + 1

    dept_breakdown = [
        {"department": k, "pending": v}
        for k, v in sorted(dept_pending.items(), key=lambda x: -x[1])
    ]

    return {
        "appeal_recommended_cases": appeal_cases,
        "compliance_required_cases": compliance_cases,
        "upcoming_deadlines_7_days": upcoming_7,
        "department_pending_breakdown": dept_breakdown,
    }


def _confidence_fusion_analytics(all_actions: list) -> Dict[str, Any]:
    """Exact aggregates over stored ``action_plan_reasoning`` payloads (audit / evaluation)."""
    keys = ("llm", "timeline", "department", "appeal")
    raw_cols = {
        "llm": "llm_confidence_raw",
        "timeline": "timeline_confidence_raw",
        "department": "department_classifier_confidence_raw",
        "appeal": "appeal_classifier_confidence_raw",
    }
    finals: List[float] = []
    effective_samples: Dict[str, List[float]] = {k: [] for k in keys}
    raw_present: Dict[str, int] = {k: 0 for k in keys}
    imputed_counts: Dict[str, int] = {k: 0 for k in keys}
    per_row: List[Dict[str, Any]] = []

    for action in all_actions:
        r = action.get("action_plan_reasoning")
        if not isinstance(r, dict):
            continue
        fin = r.get("final_action_plan_confidence")
        if fin is None:
            continue
        try:
            fin_f = float(fin)
        except (TypeError, ValueError):
            continue

        finals.append(fin_f)
        eff_map = r.get("fusion_inputs_effective_clamped01") or {}
        imp_map = r.get("subsystem_imputed_default") or {}
        contrib = r.get("weighted_contribution") or {}

        snapshot: Dict[str, Any] = {
            "action_id": action.get("id"),
            "case_number": action.get("case_number"),
            "final_action_plan_confidence": round(fin_f, 6),
        }
        for k in keys:
            ev = eff_map.get(k)
            if ev is not None:
                try:
                    effective_samples[k].append(float(ev))
                    snapshot[f"effective_{k}"] = round(float(ev), 8)
                except (TypeError, ValueError):
                    snapshot[f"effective_{k}"] = None
            else:
                snapshot[f"effective_{k}"] = None

            if imp_map.get(k):
                imputed_counts[k] += 1

            rk = raw_cols[k]
            if r.get(rk) is not None:
                raw_present[k] += 1
                try:
                    snapshot[f"raw_{k}"] = round(float(r[rk]), 8)
                except (TypeError, ValueError):
                    snapshot[f"raw_{k}"] = r.get(rk)
            else:
                snapshot[f"raw_{k}"] = None

        wk = {
            "llm": "llm_weighted",
            "timeline": "timeline_weighted",
            "department": "department_weighted",
            "appeal": "appeal_weighted",
        }
        for k, wc in wk.items():
            v = contrib.get(wc)
            if v is not None:
                try:
                    snapshot[wc] = round(float(v), 10)
                except (TypeError, ValueError):
                    snapshot[wc] = v

        per_row.append(snapshot)

    def _moments(vals: List[float]) -> Dict[str, Any]:
        if not vals:
            return {"count": 0, "mean": None, "min": None, "max": None, "pstdev": None}
        sd = pstdev(vals) if len(vals) > 1 else 0.0
        return {
            "count": len(vals),
            "mean": round(mean(vals), 8),
            "min": round(min(vals), 8),
            "max": round(max(vals), 8),
            "pstdev": round(sd, 8),
        }

    n = len(finals)
    return {
        "rows_with_fusion_reasoning": n,
        "neutral_imputation_reference": NEUTRAL_IMPUTATION,
        "default_weights_reference": default_fusion_weights(),
        "final_action_plan_confidence": _moments([round(x, 6) for x in finals]),
        "subsystem_effective_clamped01": {k: _moments(effective_samples[k]) for k in keys},
        "raw_signal_present_count": raw_present,
        "subsystem_imputed_count": imputed_counts,
        "per_action_fusion_snapshot": per_row[:500],
    }


# ── Response Schemas ──────────────────────────────


class OfficerDashboardResponse(BaseModel):
    """Response schema for officer dashboard."""

    pending_cases: int
    approved_cases: int
    completed_cases: int
    urgent_deadlines: int
    total_extracted: int
    recent_uploads: list


class AdminDashboardResponse(BaseModel):
    """Response schema for admin dashboard."""

    total_cases: int
    status_distribution: dict
    deadline_alerts: list
    department_stats: dict
    verification_counts: dict
    recent_activities: list
    verification_accuracy_trend: list
    cases_processed_per_department: list
    appeal_recommended_cases: list = Field(default_factory=list)
    compliance_required_cases: list = Field(default_factory=list)
    upcoming_deadlines_7_days: list = Field(default_factory=list)
    department_pending_breakdown: list = Field(default_factory=list)
    confidence_fusion_analytics: dict = Field(default_factory=dict)


# ── Officer Dashboard ────────────────────────────


@router.get("/officer-dashboard", response_model=OfficerDashboardResponse)
async def get_officer_dashboard(department: Optional[str] = None):
    supabase = get_supabase()

    try:
        actions_query = supabase.table("extracted_actions").select(
            "id,status,deadline,department"
        )
        if department:
            actions_query = actions_query.eq("department", department)
        actions_response = actions_query.execute()
        actions = actions_response.data if actions_response.data else []
        total_extracted = len(actions)

        pending_count = sum(1 for a in actions if a.get("status") == "pending")
        approved_count = sum(1 for a in actions if a.get("status") == "approved")
        completed_count = sum(1 for a in actions if a.get("status") == "completed")

        urgent_count = 0
        for action in actions:
            deadline = action.get("deadline")
            if deadline and is_deadline_imminent(deadline):
                urgent_count += 1

        cases_query = supabase.table("cases").select(
            "id,case_number,pdf_url,uploaded_by,created_at,department"
        )
        if department:
            cases_query = cases_query.eq("department", department)
        cases_response = cases_query.order("created_at", desc=True).limit(5).execute()
        recent_uploads = [dict(r) for r in (cases_response.data or [])]

        # Attach extracted action id for each recent case so UI can open /case/{action_id}.
        if recent_uploads:
            pdf_urls = [r.get("pdf_url") for r in recent_uploads if r.get("pdf_url")]
            if pdf_urls:
                try:
                    actions_resp = (
                        supabase.table("extracted_actions")
                        .select("id,pdf_url,created_at")
                        .in_("pdf_url", pdf_urls)
                        .order("created_at", desc=True)
                        .execute()
                    )
                    action_rows = actions_resp.data or []
                    action_id_by_url: Dict[str, str] = {}
                    for a in action_rows:
                        url = a.get("pdf_url")
                        if url and url not in action_id_by_url:
                            action_id_by_url[url] = a.get("id")
                    for row in recent_uploads:
                        url = row.get("pdf_url")
                        row["action_id"] = action_id_by_url.get(url) or ""
                except Exception:
                    for row in recent_uploads:
                        row["action_id"] = ""
            else:
                for row in recent_uploads:
                    row["action_id"] = ""

        return OfficerDashboardResponse(
            pending_cases=pending_count,
            approved_cases=approved_count,
            completed_cases=completed_count,
            urgent_deadlines=urgent_count,
            total_extracted=total_extracted,
            recent_uploads=recent_uploads,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard fetch failed: {str(e)}")


# ── Admin Dashboard ─────────────────────────────


@router.get("/admin-dashboard", response_model=AdminDashboardResponse)
async def get_admin_dashboard():
    supabase = get_supabase()
    loop = asyncio.get_event_loop()

    try:
        # ── Parallel DB fetches (previously 3 sequential round-trips) ─────
        def _fetch_cases():
            return supabase.table("cases").select("id").execute()

        def _fetch_actions():
            return (
                supabase.table("extracted_actions")
                .select(
                    "id,case_number,department,deadline,directive,status,"
                    "action_plan,action_plan_reasoning"
                )
                .execute()
            )

        def _fetch_audit():
            return (
                supabase.table("audit_logs")
                .select("id,action_type,edited_by,old_value,new_value,timestamp")
                .order("timestamp", desc=True)
                .limit(10)
                .execute()
            )

        cases_resp, actions_resp, audit_resp = await asyncio.gather(
            loop.run_in_executor(None, _fetch_cases),
            loop.run_in_executor(None, _fetch_actions),
            loop.run_in_executor(None, _fetch_audit),
        )

        all_cases   = cases_resp.data   or []
        all_actions = actions_resp.data or []
        total_cases = len(all_cases)

        gov = government_dashboard_slices(all_actions)

        status_dist: Dict[str, int] = {}
        dept_stats:  Dict[str, Dict[str, int]] = {}
        deadline_alerts: List[dict] = []
        seen_alert_cases: set = set()
        verification_counts = {"approved": 0, "rejected": 0, "edited": 0, "pending": 0}

        for action in all_actions:
            st   = action.get("status", "unknown")
            dept = action.get("department") or "Unknown"

            # status distribution
            status_dist[st] = status_dist.get(st, 0) + 1

            # department stats
            if dept not in dept_stats:
                dept_stats[dept] = {"total": 0, "pending": 0, "approved": 0,
                                    "edited": 0, "rejected": 0}
            dept_stats[dept]["total"] += 1
            dept_stats[dept][st] = dept_stats[dept].get(st, 0) + 1

            # verification counts
            if st in verification_counts:
                verification_counts[st] += 1

            # deadline alerts
            deadline = action.get("deadline")
            case_num = action.get("case_number")
            if deadline and case_num and case_num not in seen_alert_cases and is_deadline_imminent(deadline):
                deadline_info = calculate_deadline_remaining(deadline)
                deadline_alerts.append({
                    "action_id":     action.get("id"),
                    "case_number":   case_num,
                    "deadline":      deadline,
                    "days_remaining": deadline_info["days_remaining"],
                    "priority":      deadline_info["priority_level"],
                })
                seen_alert_cases.add(case_num)

        deadline_alerts.sort(
            key=lambda x: x["days_remaining"] if x["days_remaining"] is not None else 999
        )

        recent_activities = audit_resp.data or []

        today = datetime.now(timezone.utc).date()
        trend_buckets = [
            {"date": (today - timedelta(days=i)).isoformat(),
             "approved": 0, "edited": 0, "rejected": 0}
            for i in range(6, -1, -1)
        ]
        day_index = {b["date"]: b for b in trend_buckets}
        for activity in recent_activities:
            ts = activity.get("timestamp")
            if not ts:
                continue
            day_key = ts[:10]
            if day_key not in day_index:
                continue
            action_type = activity.get("action_type")
            if action_type in {"status_change", "approval"}:
                day_index[day_key]["approved"] += 1
            elif action_type in {"field_edit", "human_verification_snapshot"}:
                day_index[day_key]["edited"] += 1
            elif action_type == "rejection":
                day_index[day_key]["rejected"] += 1

        cases_processed_per_department = [
            {
                "department": dept,
                "total":      stats.get("total",    0),
                "approved":   stats.get("approved", 0),
                "pending":    stats.get("pending",  0),
            }
            for dept, stats in dept_stats.items()
        ]

        fusion_stats = _confidence_fusion_analytics(all_actions)

        return AdminDashboardResponse(
            total_cases=total_cases,
            status_distribution=status_dist,
            deadline_alerts=deadline_alerts[:10],
            department_stats=dept_stats,
            verification_counts=verification_counts,
            recent_activities=recent_activities,
            verification_accuracy_trend=trend_buckets,
            cases_processed_per_department=cases_processed_per_department,
            appeal_recommended_cases=gov["appeal_recommended_cases"],
            compliance_required_cases=gov["compliance_required_cases"],
            upcoming_deadlines_7_days=gov["upcoming_deadlines_7_days"],
            department_pending_breakdown=gov["department_pending_breakdown"],
            confidence_fusion_analytics=fusion_stats,
        )

    except Exception as e:
        logger.error("admin-dashboard failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Admin dashboard fetch failed: {str(e)}")


# ── Cases list + detail ─


def _case_passes_filters(
    row: dict,
    *,
    priority_level: Optional[str],
    action_type: Optional[str],
    deadline_days_min: Optional[int],
    deadline_days_max: Optional[int],
) -> bool:
    ap = row.get("action_plan") or {}
    if priority_level and ap.get("priority_level") != priority_level:
        return False
    if action_type and ap.get("action_type") != action_type:
        return False
    if deadline_days_min is not None or deadline_days_max is not None:
        dl = ap.get("compliance_deadline") or row.get("deadline")
        if not dl:
            return False
        info = calculate_deadline_remaining(str(dl))
        dr = info.get("days_remaining")
        if dr is None:
            return False
        if deadline_days_min is not None and dr < deadline_days_min:
            return False
        if deadline_days_max is not None and dr > deadline_days_max:
            return False
    return True


@router.get("/cases")
async def get_cases(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    department: Optional[str] = None,
    case_number: Optional[str] = None,
    priority_level: Optional[str] = None,
    action_type: Optional[str] = None,
    deadline_range_min_days: Optional[int] = None,
    deadline_range_max_days: Optional[int] = None,
):
    """
    Cases list with server-side filtering where possible.
    action_plan-backed fields (priority_level, action_type, deadline_days) are
    applied in-process after a capped DB fetch (max 2000 rows).
    """
    supabase = get_supabase()
    _DB_ROW_CAP = 2000  # hard ceiling to prevent OOM on large tables

    try:
        query = supabase.table("extracted_actions").select("*")

        # Push supported filters to DB to shrink the result set before Python sees it
        if status:
            query = query.eq("status", status)
        if department:
            query = query.eq("department", department)
        if case_number:
            query = query.ilike("case_number", f"%{case_number}%")

        response = (
            query
            .order("created_at", desc=True)
            .limit(_DB_ROW_CAP)
            .execute()
        )
        rows = response.data or []

        # In-process filter for action_plan-backed fields
        needs_post_filter = any([
            priority_level,
            action_type,
            deadline_range_min_days is not None,
            deadline_range_max_days is not None,
        ])

        if needs_post_filter:
            filtered = [
                r for r in rows
                if _case_passes_filters(
                    r,
                    priority_level=priority_level,
                    action_type=action_type,
                    deadline_days_min=deadline_range_min_days,
                    deadline_days_max=deadline_range_max_days,
                )
            ]
        else:
            filtered = rows

        slice_ = filtered[skip: skip + limit]
        return {
            "total": len(filtered),
            "data": slice_,
            "skip": skip,
            "limit": limit,
            "capped": len(rows) >= _DB_ROW_CAP,  # signal to client if result may be truncated
        }

    except Exception as e:
        logger.error("get_cases failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Cases fetch failed: {str(e)}")


@router.get("/cases/{action_id}")
async def get_case_details(action_id: str):
    supabase = get_supabase()
    try:
        action_resp = (
            supabase.table("extracted_actions")
            .select("*")
            .eq("id", action_id)
            .limit(1)
            .execute()
        )
        if not action_resp.data:
            raise HTTPException(status_code=404, detail="Case/action not found")
        action = action_resp.data[0]

        audit_resp = (
            supabase.table("audit_logs")
            .select("*")
            .eq("case_id", action_id)
            .order("timestamp", desc=True)
            .execute()
        )
        audit_logs = audit_resp.data if audit_resp.data else []

        deadline_info = None
        if action.get("deadline"):
            deadline_info = calculate_deadline_remaining(action.get("deadline"))

        layout_blocks = None
        if action.get("pdf_url"):
            cresp = (
                supabase.table("cases")
                .select("layout_blocks")
                .eq("pdf_url", action["pdf_url"])
                .limit(1)
                .execute()
            )
            if cresp.data:
                layout_blocks = cresp.data[0].get("layout_blocks")
            # If layout_blocks are missing, return [] — the pipeline will
            # backfill them on next extraction. Do NOT re-download the PDF
            # inside a synchronous GET handler (OOM risk + blocks uvicorn thread).
            if not layout_blocks:
                layout_blocks = []

        ap = action.get("action_plan") or {}
        deadline_for_hl = ap.get("compliance_deadline") or action.get("deadline")

        jd_iso = None
        if action.get("judgment_date"):
            jd_iso = str(action.get("judgment_date"))[:10]
        comp_dl = ap.get("compliance_deadline")
        app_dl = ap.get("appeal_deadline")

        pdf_highlights = layout_blocks_to_highlights(
            layout_blocks,
            action.get("directive"),
            str(deadline_for_hl) if deadline_for_hl else None,
            source_sentence=action.get("source_sentence"),
            judgment_date_iso=jd_iso,
            compliance_deadline=str(comp_dl)[:10] if comp_dl else None,
            appeal_deadline=str(app_dl)[:10] if app_dl else None,
        )

        return {
            "action": action,
            "deadline_info": deadline_info,
            "audit_logs": audit_logs,
            "layout_blocks": layout_blocks or [],
            "pdf_highlights": pdf_highlights,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Case details fetch failed: {str(e)}")


@router.get("/cases/{action_id}/analytics")
async def get_case_analytics(action_id: str):
    """Get comprehensive analytics for an approved/extracted case, similar to post-upload display."""
    supabase = get_supabase()
    try:
        action_resp = (
            supabase.table("extracted_actions")
            .select("*")
            .eq("id", action_id)
            .limit(1)
            .execute()
        )
        if not action_resp.data:
            raise HTTPException(status_code=404, detail="Case/action not found")
        
        action = action_resp.data[0]
        ap = action.get("action_plan") or {}
        reasoning = action.get("action_plan_reasoning") or {}
        
        # Build confidence score using same logic as frontend
        def coerce_fused_score():
            r = reasoning.get("final_action_plan_confidence")
            if isinstance(r, (int, float)) and not isinstance(r, bool) and not __import__('math').isnan(float(r)):
                return min(1, max(0, float(r)))
            if r is not None and r != "":
                try:
                    n = float(r)
                    return min(1, max(0, n))
                except (TypeError, ValueError):
                    pass
            ac = ap.get("confidence_score")
            if ac is not None and ac != "":
                try:
                    n = float(ac) if isinstance(ac, (int, float)) else float(ac)
                    return min(1, max(0, n))
                except (TypeError, ValueError):
                    pass
            ec = action.get("confidence_score")
            if ec is not None and ec != "":
                try:
                    n = float(ec) if isinstance(ec, (int, float)) else float(ec)
                    return min(1, max(0, n))
                except (TypeError, ValueError):
                    pass
            return 0
        
        fused_score = coerce_fused_score()
        
        # Build fusion subsystem analytics
        effMap = reasoning.get("fusion_inputs_effective_clamped01") or {}
        wMap = reasoning.get("weights") or {}
        contribMap = reasoning.get("weighted_contribution") or {}
        impMap = reasoning.get("subsystem_imputed_default") or {}
        
        fusion_rows = []
        keys = ["llm", "timeline", "department", "appeal"]
        raw_cols = {
            "llm": "llm_confidence_raw",
            "timeline": "timeline_confidence_raw",
            "department": "department_classifier_confidence_raw",
            "appeal": "appeal_classifier_confidence_raw",
        }
        
        for key in keys:
            row = {
                "key": key,
                "label": {
                    "llm": "LLM extraction",
                    "timeline": "Timeline parser",
                    "department": "Department classifier",
                    "appeal": "Appeal recommender",
                }.get(key),
                "effective": effMap.get(key),
                "weight": wMap.get(key),
                "contribution": contribMap.get(f"{key}_weighted"),
                "raw": reasoning.get(raw_cols[key]),
                "imputed": impMap.get(key, False),
            }
            fusion_rows.append(row)
        
        # Get audit logs
        audit_resp = (
            supabase.table("audit_logs")
            .select("*")
            .eq("case_id", action_id)
            .order("timestamp", desc=True)
            .execute()
        )
        audit_logs = audit_resp.data if audit_resp.data else []
        
        # Calculate verification metrics
        approval_log = next((log for log in audit_logs if log.get("action_type") in ["approval", "status_change"]), None)
        approval_timestamp = approval_log.get("timestamp") if approval_log else action.get("updated_at")
        
        # Build response with analytics
        return {
            "action_id": action_id,
            "status": action.get("status"),
            "case_number": action.get("case_number"),
            "department": ap.get("department") or action.get("department"),
            "judgment_date": action.get("judgment_date"),
            "directive": action.get("directive"),
            "confidence_score": fused_score,
            "confidence_label": "HIGH" if fused_score >= 0.8 else "MEDIUM" if fused_score >= 0.6 else "LOW",
            "action_plan": ap,
            "reasoning": reasoning,
            "fusion_analytics": {
                "final_score": fused_score,
                "subsystems": fusion_rows,
                "has_reasoning": bool(reasoning),
            },
            "audit_logs": audit_logs[:20],
            "approval_info": {
                "status": action.get("status"),
                "approved_by": approval_log.get("user_email") if approval_log else None,
                "approved_at": approval_timestamp,
                "created_at": action.get("created_at"),
                "updated_at": action.get("updated_at"),
            },
            "metadata": {
                "priority_level": ap.get("priority_level"),
                "action_type": ap.get("action_type"),
                "appeal_recommended": ap.get("appeal_recommended"),
                "compliance_deadline": ap.get("compliance_deadline"),
                "appeal_deadline": ap.get("appeal_deadline"),
            },
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Case analytics fetch failed: {str(e)}")
