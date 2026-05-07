"""
Extract Router — synchronous and asynchronous extraction flows.

Key changes vs previous version:
  - Removed global extraction_lock that serialised ALL background jobs.
    (Render free tier runs 1 uvicorn worker; the lock added no safety
    but caused cascade timeouts when a job took > the next job's queue wait.)
  - Per-job request_id propagated to pipeline for correlated log tracing.
  - Structured error payloads: {stage, error, request_id} instead of bare str.
  - Status endpoint: if job_id unknown (process restart) → 410 Gone with
    explanation instead of 404, so frontend can show a helpful message.
  - Stage field in job store lets frontend show granular progress.
  - Meaningful JSON error bodies replace generic 400/500.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from backend.services.pipeline import (
    build_extraction_artifacts,
    insert_extraction_record,
    persist_extraction_record,
    run_pdf_and_llm,
    run_secondary_case_updates,
)
from backend.services.processing_state import (
    build_completed_result,
    fetch_case_by_pdf_url,
    fetch_case_by_job_id,
    fetch_latest_action_by_pdf_url,
    recover_processing_case,
    update_case_processing_status,
    update_case_status,
)

logger = logging.getLogger("judgeai.extract")

router = APIRouter()
EXTRACTION_JOB_STORE: Dict[str, Dict[str, Any]] = {}
_MAX_JOBS_RETAINED = 100   # increased; on 512 MB these dicts are tiny


def _cleanup_job_store() -> None:
    """Keep only the most recent N jobs to prevent unbounded memory growth."""
    while len(EXTRACTION_JOB_STORE) > _MAX_JOBS_RETAINED:
        oldest_job_id = min(
            EXTRACTION_JOB_STORE,
            key=lambda job_id: EXTRACTION_JOB_STORE[job_id].get("created_at") or "",
        )
        job = EXTRACTION_JOB_STORE.get(oldest_job_id) or {}
        if job.get("status") in {"queued", "processing"}:
            break
        del EXTRACTION_JOB_STORE[oldest_job_id]


class ExtractRequest(BaseModel):
    pdf_url: str


# ── Background job runner ─────────────────────────────────────
def _set_job_stage(
    job_id: str,
    pdf_url: str,
    stage: str,
    *,
    status: str = "processing",
    error: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
) -> None:
    store = EXTRACTION_JOB_STORE[job_id]
    heartbeat_at = datetime.now(timezone.utc).isoformat()
    store["status"] = status
    store["stage"] = stage
    store["heartbeat_at"] = heartbeat_at
    if started_at is not None:
        store["started_at"] = started_at
    if finished_at is not None:
        store["finished_at"] = finished_at
    if error is not None:
        store["error"] = error
        store["error_stage"] = stage

    try:
        update_case_processing_status(
            pdf_url,
            status,
            stage,
            job_id=job_id,
            error=error,
            started_at=started_at,
            finished_at=finished_at,
            heartbeat_at=heartbeat_at,
            clear_error=error is None and status != "failed",
        )
    except Exception as exc:
        logger.error(
            "[extract] Failed to sync processing state job=%s stage=%s: %s",
            job_id,
            stage,
            exc,
            exc_info=True,
        )


def _run_single_extraction_job(job_id: str, pdf_url: str) -> None:
    """
    Executed by FastAPI BackgroundTasks in a thread.
    Updates EXTRACTION_JOB_STORE at every stage so polling has granularity.
    Also writes processing_status to Supabase so progress survives restarts.
    """
    request_id = job_id[:8]
    started_iso = datetime.now(timezone.utc).isoformat()
    logger.info("BACKGROUND_TASK_STARTED request_id=%s job_id=%s pdf_url=%s", request_id, job_id, pdf_url[:120])
    t_total = time.monotonic()
    _set_job_stage(job_id, pdf_url, "pdf_extraction", started_at=started_iso)

    try:
        logger.info("EXTRACTION_STARTED request_id=%s job_id=%s", request_id, job_id)
        _set_job_stage(job_id, pdf_url, "pdf_extraction")
        extracted_data, extracted_text, layout_blocks = run_pdf_and_llm(
            pdf_url, request_id=request_id
        )
        logger.info(
            "EXTRACTION_COMPLETED request_id=%s job_id=%s chars=%d blocks=%d",
            request_id,
            job_id,
            len(extracted_text or ""),
            len(layout_blocks or []),
        )

        _set_job_stage(job_id, pdf_url, "analytics_generation")
        artifacts = build_extraction_artifacts(
            pdf_url,
            extracted_data,
            extracted_text,
            request_id=request_id,
        )
        logger.info("ANALYTICS_GENERATED request_id=%s job_id=%s", request_id, job_id)

        _set_job_stage(job_id, pdf_url, "db_persist")
        result = insert_extraction_record(artifacts["record"], request_id=request_id)
        out = {
            "message": "Extraction completed successfully",
            "workflow_status": "completed",
            "action_status": artifacts["record"]["status"],
            "extracted_data": artifacts["safe_extracted_data"],
            "action_plan": artifacts["safe_action_plan"],
            "action_plan_reasoning": artifacts["safe_reasoning"],
            "db_record": result.data,
        }

        db_row = (out.get("db_record") or [{}])[0]
        action_id = db_row.get("id")
        try:
            _set_job_stage(job_id, pdf_url, "secondary_enrichment")
            run_secondary_case_updates(
                pdf_url=pdf_url,
                extracted_text=extracted_text,
                layout_blocks=layout_blocks,
                request_id=request_id,
            )
        except Exception as secondary_exc:
            logger.error(
                "[extract] req=%s job=%s secondary updates failed after primary insert: %s",
                request_id,
                job_id,
                str(secondary_exc)[:200],
                exc_info=True,
            )

        finished_iso = datetime.now(timezone.utc).isoformat()
        EXTRACTION_JOB_STORE[job_id].update(
            {"result": out, "action_id": action_id}
        )
        _set_job_stage(job_id, pdf_url, "completed", status="completed", finished_at=finished_iso)
        try:
            update_case_status(pdf_url, "completed")
        except Exception as case_status_exc:
            logger.error(
                "[extract] req=%s job=%s completion status write failed after insert action_id=%s: %s",
                request_id,
                job_id,
                action_id,
                str(case_status_exc)[:200],
                exc_info=True,
            )
            raise

        logger.info(
            "JOB_COMPLETED request_id=%s job_id=%s elapsed=%.2fs action_id=%s",
            request_id, job_id, time.monotonic() - t_total, action_id,
        )

    except Exception as exc:
        stage = (EXTRACTION_JOB_STORE.get(job_id) or {}).get("stage", "unknown")
        finished_iso = datetime.now(timezone.utc).isoformat()
        _set_job_stage(
            job_id,
            pdf_url,
            stage,
            status="failed",
            error=str(exc),
            finished_at=finished_iso,
        )
        # Revert case.status back to pending so it reappears in queue
        try:
            update_case_status(pdf_url, "pending")
        except Exception as case_status_exc:
            logger.error(
                "[extract] Failed to reset case status to pending for %s: %s",
                pdf_url,
                case_status_exc,
                exc_info=True,
            )

        logger.error(
            "JOB_FAILED request_id=%s job_id=%s stage=%s elapsed=%.2fs error=%s",
            request_id, job_id, stage, time.monotonic() - t_total, str(exc)[:200],
            exc_info=True,
        )



# ── Synchronous endpoint (kept for compatibility / admin use) ─

@router.post("/extract-actions")
async def extract_actions(payload: ExtractRequest):
    """Synchronous extraction — blocks until complete. Prefer async variant."""
    request_id = uuid.uuid4().hex[:8]
    try:
        extracted_data, extracted_text, layout_blocks = run_pdf_and_llm(
            payload.pdf_url, request_id=request_id
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail={"error": str(e), "request_id": request_id})
    except Exception as e:
        logger.error("[extract] sync req=%s unexpected: %s", request_id, e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": f"Extraction failed: {e}", "request_id": request_id},
        )

    try:
        return persist_extraction_record(
            payload.pdf_url, extracted_data, extracted_text, layout_blocks,
            request_id=request_id,
        )
    except Exception as e:
        logger.error("[extract] sync req=%s db persist failed: %s", request_id, e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": f"Database persist failed: {e}", "request_id": request_id},
        )


# ── Async (queue) endpoint ─────────────────────────────────────

@router.post("/extract-actions-async")
async def extract_actions_async(payload: ExtractRequest, background_tasks: BackgroundTasks):
    """Queue extraction so the upload call returns immediately."""
    job_id = uuid.uuid4().hex
    created_at = datetime.now(timezone.utc).isoformat()
    EXTRACTION_JOB_STORE[job_id] = {
        "job_id": job_id,
        "pdf_url": payload.pdf_url,
        "status": "queued",
        "stage": "queued",
        "created_at": created_at,
        "started_at": None,
        "finished_at": None,
        "error": None,
        "error_stage": None,
        "action_id": None,
        "result": None,
    }

    logger.info("UPLOAD_RECEIVED job_id=%s pdf_url=%s", job_id, payload.pdf_url[:120])
    try:
        update_case_status(payload.pdf_url, "processing")
        update_case_processing_status(
            payload.pdf_url,
            "queued",
            "queued",
            job_id=job_id,
            started_at=created_at,
            clear_error=True,
        )
    except Exception as e:
        logger.warning("[extract] pre-queue case status update failed: %s", e)

    background_tasks.add_task(_run_single_extraction_job, job_id, payload.pdf_url)
    _cleanup_job_store()

    logger.info("[extract] job=%s queued url=%s", job_id, payload.pdf_url[:80])
    return {
        "job_id": job_id,
        "status": "queued",
        "stage": "queued",
        "message": "Extraction queued. Processing in background.",
        "pdf_url": payload.pdf_url,
    }


# ── Status polling endpoint ────────────────────────────────────

@router.get("/extract-actions-status/{job_id}")
async def extract_actions_status(job_id: str):
    """
    Poll extraction job status.

    Two-tier lookup:
    1. In-memory EXTRACTION_JOB_STORE  — fast path (same process lifetime)
    2. Supabase cases.processing_*     — fallback when backend restarted

    Returns 410 Gone only if BOTH lookups fail (e.g., invalid job_id).
    """
    job = EXTRACTION_JOB_STORE.get(job_id)

    if job:
        # ── Fast path: job is in memory ──────────────────────
        response: Dict[str, Any] = {
            "job_id":      job_id,
            "status":      job.get("status"),
            "stage":       job.get("stage"),
            "created_at":  job.get("created_at"),
            "started_at":  job.get("started_at"),
            "finished_at": job.get("finished_at"),
            "pdf_url":     job.get("pdf_url"),
            "action_id":   job.get("action_id"),
            "heartbeat_at": job.get("heartbeat_at") or job.get("finished_at") or job.get("started_at"),
            "source":      "memory",
        }
        if job.get("status") == "failed":
            response["error"]       = job.get("error")
            response["error_stage"] = job.get("error_stage")

        if job.get("status") == "completed":
            result = job.get("result") or {}
            response["result"] = {
                "message":        result.get("message"),
                "status":         result.get("workflow_status") or result.get("status"),
                "action_status":  result.get("action_status"),
                "extracted_data": result.get("extracted_data"),
                "action_plan":    result.get("action_plan"),
                "action_plan_reasoning": result.get("action_plan_reasoning"),
                "db_record":      result.get("db_record"),
            }
        logger.info(
            "POLLING_RESPONSE_SENT job_id=%s source=memory status=%s stage=%s",
            job_id,
            response["status"],
            response["stage"],
        )
        return response

    # ── Slow path: check Supabase (backend may have restarted) ──
    try:
        row = fetch_case_by_job_id(job_id)
    except Exception as exc:
        logger.warning("[extract] extract-actions-status job lookup failed: %s", exc, exc_info=True)
        row = None

    if row:
        latest_action = None
        try:
            latest_action = fetch_latest_action_by_pdf_url(row["pdf_url"])
        except Exception as exc:
            logger.warning("[extract] extract-actions-status action lookup failed: %s", exc, exc_info=True)
        recovered = recover_processing_case(row, latest_action)
        response = {
            "job_id": job_id,
            "status": recovered["status"],
            "stage": recovered["stage"],
            "created_at": row.get("processing_started_at") or row.get("updated_at"),
            "started_at": row.get("processing_started_at"),
            "finished_at": recovered.get("finished_at") or row.get("processing_finished_at"),
            "pdf_url": row.get("pdf_url"),
            "action_id": recovered.get("action_id"),
            "error": recovered.get("error"),
            "error_stage": recovered.get("error_stage"),
            "heartbeat_at": recovered.get("heartbeat_at") or row.get("processing_heartbeat_at"),
            "source": "database",
            "result": recovered.get("result"),
        }
        logger.info(
            "POLLING_RESPONSE_SENT job_id=%s source=database status=%s stage=%s",
            job_id,
            response["status"],
            response["stage"],
        )
        return response

    raise HTTPException(
        status_code=410,
        detail={
            "error": (
                "Extraction job not found. The backend may have restarted "
                "during processing. Please check the case list — your document "
                "may have been partially or fully processed."
            ),
            "job_id":      job_id,
            "suggestion":  "check_case_list",
            "hint":        (
                "Each uploaded case row in Supabase now stores processing_status, "
                "processing_stage, and processing_job_id columns updated in real-time. "
                "Refresh the case list to see the latest state."
            ),
        },
    )


# ── DB-based processing status (restart-resilient) ────────────

@router.get("/case-processing-status")
async def case_processing_status(pdf_url: str):
    """
    Query processing status for a case by its PDF URL directly from Supabase.

    Unlike /extract-actions-status/{job_id} (which relies on in-memory state),
    this endpoint reads from the `cases` table columns written by the background
    job on every stage transition.  It survives backend restarts.

    Frontend usage:
      - Use as fallback when /extract-actions-status returns 410.
      - Or poll this endpoint exclusively after upload for a simpler approach.
    """
    try:
        row = fetch_case_by_pdf_url(pdf_url)
    except Exception as exc:
        logger.warning("[extract] case-processing-status DB query failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=503, detail=f"Database query failed: {exc}")

    if not row:
        raise HTTPException(
            status_code=404,
            detail={"error": "No case found for this PDF URL.", "pdf_url": pdf_url},
        )

    latest_action = None
    try:
        latest_action = fetch_latest_action_by_pdf_url(pdf_url)
    except Exception as exc:
        logger.warning("[extract] action lookup during status check failed: %s", exc, exc_info=True)

    current_status = row.get("processing_status")
    if current_status == "processing":
        recovered = recover_processing_case(row, latest_action)
        status = recovered["status"]
        stage = recovered["stage"]
        error = recovered.get("error")
        finished_at = recovered.get("finished_at") or row.get("processing_finished_at")
        result = recovered.get("result")
        action_id = recovered.get("action_id")
    else:
        stage = row.get("processing_stage") or "unknown"
        error = row.get("processing_error")
        finished_at = row.get("processing_finished_at")
        legacy = row.get("status", "unknown")
        status = (
            "completed" if current_status == "completed" or legacy == "completed"
            else "failed" if current_status == "failed"
            else "processing" if current_status == "processing" or legacy == "processing"
            else "queued"
        )
        result = build_completed_result(latest_action) if latest_action and status == "completed" else None
        action_id = latest_action.get("id") if latest_action else None

    payload = {
        "case_id":     row.get("id"),
        "case_number": row.get("case_number"),
        "pdf_url":     pdf_url,
        "status":      status,
        "stage":       stage,
        "error":       error,
        "started_at":  row.get("processing_started_at"),
        "finished_at": finished_at,
        "heartbeat_at": row.get("processing_heartbeat_at"),
        "job_id": row.get("processing_job_id"),
        "source":      "database",
        "result": result,
        "action_id": action_id,
    }
    logger.info(
        "POLLING_RESPONSE_SENT pdf_url=%s source=database status=%s stage=%s",
        pdf_url[:120],
        payload["status"],
        payload["stage"],
    )
    return payload
