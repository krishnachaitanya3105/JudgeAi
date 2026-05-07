from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.config import get_supabase

logger = logging.getLogger("judgeai.processing_state")

PROCESSING_STALE_AFTER_SEC = int(os.getenv("JUDGEAI_PROCESSING_STALE_AFTER_SEC", "180"))
RECOVERY_SCAN_LIMIT = int(os.getenv("JUDGEAI_RECOVERY_SCAN_LIMIT", "50"))
_KNOWN_CASES_COLUMNS = {
    "id",
    "case_number",
    "pdf_url",
    "status",
    "updated_at",
    "processing_status",
    "processing_stage",
    "processing_error",
    "processing_started_at",
    "processing_finished_at",
    "processing_job_id",
    "processing_heartbeat_at",
}


def _extract_missing_column(exc: Exception) -> Optional[str]:
    text = str(exc)
    match = re.search(
        r"(?:column\s+cases\.|the\s+')([a-zA-Z0-9_]+)(?:\s+does not exist|' column of 'cases' in the schema cache)",
        text,
    )
    return match.group(1) if match else None


def _cases_select_where(where_builder, *, columns: list[str]) -> Any:
    current = [col for col in columns if col in _KNOWN_CASES_COLUMNS]
    while True:
        try:
            return where_builder(get_supabase().table("cases").select(",".join(current))).execute()
        except Exception as exc:
            missing = _extract_missing_column(exc)
            if missing and missing in current:
                _KNOWN_CASES_COLUMNS.discard(missing)
                current = [col for col in current if col != missing]
                logger.warning("Cases column unavailable at runtime, falling back without `%s`", missing)
                continue
            raise


def _cases_update_by_pdf_url(pdf_url: str, update: Dict[str, Any]) -> Any:
    current = dict(update)
    while True:
        try:
            return get_supabase().table("cases").update(current).eq("pdf_url", pdf_url).execute()
        except Exception as exc:
            missing = _extract_missing_column(exc)
            if missing and missing in current:
                _KNOWN_CASES_COLUMNS.discard(missing)
                current.pop(missing, None)
                logger.warning("Cases column unavailable at runtime, skipping `%s` updates", missing)
                if not current:
                    return None
                continue
            raise


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def update_case_processing_status(
    pdf_url: str,
    processing_status: str,
    processing_stage: str,
    *,
    job_id: Optional[str] = None,
    error: Optional[str] = None,
    started_at: Optional[str] = None,
    finished_at: Optional[str] = None,
    heartbeat_at: Optional[str] = None,
    clear_error: bool = False,
) -> Any:
    update: Dict[str, Any] = {
        "processing_status": processing_status,
        "processing_stage": processing_stage,
        "processing_heartbeat_at": heartbeat_at or now_iso(),
    }
    if job_id is not None:
        update["processing_job_id"] = job_id
    if error is not None:
        update["processing_error"] = error[:1000]
    elif clear_error:
        update["processing_error"] = None
    if started_at is not None:
        update["processing_started_at"] = started_at
    if finished_at is not None:
        update["processing_finished_at"] = finished_at

    logger.info(
        "STATUS_UPDATED pdf_url=%s status=%s stage=%s job_id=%s",
        pdf_url[:120],
        processing_status,
        processing_stage,
        job_id,
    )
    return _cases_update_by_pdf_url(pdf_url, update)


def update_case_status(pdf_url: str, status: str) -> Any:
    logger.info("STATUS_UPDATED pdf_url=%s case_status=%s", pdf_url[:120], status)
    return _cases_update_by_pdf_url(pdf_url, {"status": status})


def fetch_case_by_pdf_url(pdf_url: str) -> Optional[Dict[str, Any]]:
    resp = _cases_select_where(
        lambda table: table.eq("pdf_url", pdf_url).limit(1),
        columns=[
            "id",
            "case_number",
            "pdf_url",
            "status",
            "updated_at",
            "processing_status",
            "processing_stage",
            "processing_error",
            "processing_started_at",
            "processing_finished_at",
            "processing_job_id",
            "processing_heartbeat_at",
        ],
    )
    rows = resp.data or []
    return rows[0] if rows else None


def fetch_case_by_job_id(job_id: str) -> Optional[Dict[str, Any]]:
    if "processing_job_id" not in _KNOWN_CASES_COLUMNS:
        return None
    try:
        resp = _cases_select_where(
            lambda table: table.eq("processing_job_id", job_id).limit(1),
            columns=[
                "id",
                "case_number",
                "pdf_url",
                "status",
                "updated_at",
                "processing_status",
                "processing_stage",
                "processing_error",
                "processing_started_at",
                "processing_finished_at",
                "processing_job_id",
                "processing_heartbeat_at",
            ],
        )
    except Exception as exc:
        missing = _extract_missing_column(exc)
        if missing == "processing_job_id":
            _KNOWN_CASES_COLUMNS.discard("processing_job_id")
            logger.warning("Cases column unavailable at runtime, restart-safe job lookup disabled")
            return None
        raise
    rows = resp.data or []
    return rows[0] if rows else None


def fetch_latest_action_by_pdf_url(pdf_url: str) -> Optional[Dict[str, Any]]:
    resp = (
        get_supabase()
        .table("extracted_actions")
        .select(
            "id,case_number,status,created_at,pdf_url,action_plan,action_plan_reasoning,"
            "judgment_date,department,deadline,directive,confidence_score,source_sentence"
        )
        .eq("pdf_url", pdf_url)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    return rows[0] if rows else None


def _row_age_sec(row: Dict[str, Any]) -> Optional[float]:
    anchor = (
        row.get("processing_heartbeat_at")
        or row.get("updated_at")
        or row.get("processing_started_at")
    )
    if not anchor:
        return None
    try:
        parsed = datetime.fromisoformat(str(anchor).replace("Z", "+00:00"))
        return max(0.0, (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds())
    except Exception:
        return None


def build_completed_result(latest_action: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "message": "Extraction completed successfully",
        "status": "completed",
        "action_status": latest_action.get("status"),
        "extracted_data": {
            "case_number": latest_action.get("case_number"),
            "judgment_date": latest_action.get("judgment_date"),
            "department": latest_action.get("department"),
            "deadline": latest_action.get("deadline"),
            "directive": latest_action.get("directive"),
            "confidence_score": latest_action.get("confidence_score"),
            "source_sentence": latest_action.get("source_sentence"),
        },
        "action_plan": latest_action.get("action_plan"),
        "action_plan_reasoning": latest_action.get("action_plan_reasoning"),
        "db_record": [latest_action],
    }


def recover_processing_case(
    row: Dict[str, Any],
    latest_action: Optional[Dict[str, Any]] = None,
    *,
    force: bool = False,
) -> Dict[str, Any]:
    pdf_url = row["pdf_url"]
    job_id = row.get("processing_job_id")
    age_sec = _row_age_sec(row)
    latest_action = latest_action if latest_action is not None else fetch_latest_action_by_pdf_url(pdf_url)

    if latest_action:
        finished_at = now_iso()
        update_case_processing_status(
            pdf_url,
            "completed",
            "completed",
            job_id=job_id,
            finished_at=finished_at,
            clear_error=True,
        )
        update_case_status(pdf_url, "completed")
        logger.warning(
            "JOB_COMPLETED recovered=true pdf_url=%s action_id=%s age_sec=%s",
            pdf_url[:120],
            latest_action.get("id"),
            round(age_sec, 1) if age_sec is not None else None,
        )
        return {
            "status": "completed",
            "stage": "completed",
            "finished_at": finished_at,
            "result": build_completed_result(latest_action),
            "action_id": latest_action.get("id"),
            "recovered": True,
        }

    should_fail = force or (age_sec is not None and age_sec >= PROCESSING_STALE_AFTER_SEC)
    if should_fail:
        finished_at = now_iso()
        message = (
            f"Processing stalled during {row.get('processing_stage') or 'unknown'} for "
            f"{int(age_sec)}s and no persisted action record was found. "
            "The worker likely restarted or was terminated before the job finished."
            if age_sec is not None
            else "Processing stalled and no persisted action record was found."
        )
        update_case_processing_status(
            pdf_url,
            "failed",
            row.get("processing_stage") or "unknown",
            job_id=job_id,
            error=message,
            finished_at=finished_at,
        )
        update_case_status(pdf_url, "pending")
        logger.error(
            "JOB_FAILED recovered=true pdf_url=%s stage=%s age_sec=%s error=%s",
            pdf_url[:120],
            row.get("processing_stage"),
            round(age_sec, 1) if age_sec is not None else None,
            message,
        )
        return {
            "status": "failed",
            "stage": row.get("processing_stage") or "unknown",
            "error": message,
            "error_stage": row.get("processing_stage") or "unknown",
            "finished_at": finished_at,
            "recovered": True,
        }

    return {
        "status": row.get("processing_status") or "processing",
        "stage": row.get("processing_stage") or "processing",
        "error": row.get("processing_error"),
        "finished_at": row.get("processing_finished_at"),
        "heartbeat_at": row.get("processing_heartbeat_at"),
        "action_id": latest_action.get("id") if latest_action else None,
        "recovered": False,
    }


def recover_stale_processing_cases(limit: int = RECOVERY_SCAN_LIMIT) -> Dict[str, int]:
    try:
        if "processing_status" not in _KNOWN_CASES_COLUMNS:
            return {"completed": 0, "failed": 0}
        resp = _cases_select_where(
            lambda table: table.eq("processing_status", "processing").order("updated_at", desc=False).limit(limit),
            columns=[
                "id",
                "case_number",
                "pdf_url",
                "status",
                "updated_at",
                "processing_status",
                "processing_stage",
                "processing_error",
                "processing_started_at",
                "processing_finished_at",
                "processing_job_id",
                "processing_heartbeat_at",
            ],
        )
    except Exception as exc:
        logger.error("Startup recovery query failed: %s", exc, exc_info=True)
        return {"completed": 0, "failed": 0}

    completed = 0
    failed = 0
    for row in resp.data or []:
        try:
            outcome = recover_processing_case(row)
            if outcome["recovered"] and outcome["status"] == "completed":
                completed += 1
            elif outcome["recovered"] and outcome["status"] == "failed":
                failed += 1
        except Exception as exc:
            logger.error(
                "Startup recovery failed for pdf_url=%s: %s",
                row.get("pdf_url"),
                exc,
                exc_info=True,
            )

    if completed or failed:
        logger.warning(
            "Recovered stale processing cases: completed=%d failed=%d",
            completed,
            failed,
        )
    return {"completed": completed, "failed": failed}
