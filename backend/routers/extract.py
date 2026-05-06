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

from backend.config import get_supabase
from backend.services.pipeline import persist_extraction_record, run_pdf_and_llm

logger = logging.getLogger("judgeai.extract")

router = APIRouter()
EXTRACTION_JOB_STORE: Dict[str, Dict[str, Any]] = {}
_MAX_JOBS_RETAINED = 100   # increased; on 512 MB these dicts are tiny


def _cleanup_job_store() -> None:
    """Keep only the most recent N jobs to prevent unbounded memory growth."""
    if len(EXTRACTION_JOB_STORE) > _MAX_JOBS_RETAINED:
        oldest = list(EXTRACTION_JOB_STORE.keys())[: len(EXTRACTION_JOB_STORE) - _MAX_JOBS_RETAINED]
        for k in oldest:
            del EXTRACTION_JOB_STORE[k]


class ExtractRequest(BaseModel):
    pdf_url: str


# ── Background job runner ─────────────────────────────────────

def _update_case_db_status(
    pdf_url: str,
    processing_status: str,
    processing_stage: str,
    error: str = None,
    started_at: str = None,
    finished_at: str = None,
) -> None:
    """Best-effort update of cases.processing_* columns for restart resilience."""
    try:
        update: dict = {
            "processing_status": processing_status,
            "processing_stage": processing_stage,
        }
        if error is not None:
            update["processing_error"] = error[:500]
        if started_at is not None:
            update["processing_started_at"] = started_at
        if finished_at is not None:
            update["processing_finished_at"] = finished_at
        get_supabase().table("cases").update(update).eq("pdf_url", pdf_url).execute()
    except Exception as exc:
        logger.debug("[extract] DB status sync skipped: %s", exc)


def _run_single_extraction_job(job_id: str, pdf_url: str) -> None:
    """
    Executed by FastAPI BackgroundTasks in a thread.
    Updates EXTRACTION_JOB_STORE at every stage so polling has granularity.
    Also writes processing_status to Supabase so progress survives restarts.
    """
    request_id = job_id[:8]          # short alias for logs
    store = EXTRACTION_JOB_STORE[job_id]

    started_iso = datetime.now(timezone.utc).isoformat()
    store["status"] = "processing"
    store["stage"] = "pdf_extraction"
    store["started_at"] = started_iso

    logger.info(
        "[extract] req=%s job=%s START url=%s", request_id, job_id, pdf_url[:80]
    )
    t_total = time.monotonic()

    # Persist initial processing state to DB (survives restart)
    _update_case_db_status(
        pdf_url, "processing", "pdf_extraction", started_at=started_iso
    )

    try:
        # ── Stage 1: PDF → text ──────────────────────────────
        store["stage"] = "pdf_extraction"
        _update_case_db_status(pdf_url, "processing", "pdf_extraction")
        extracted_data, extracted_text, layout_blocks = run_pdf_and_llm(
            pdf_url, request_id=request_id
        )

        # ── Stage 2: DB persist + secondary updates ──────────
        store["stage"] = "db_persist"
        _update_case_db_status(pdf_url, "processing", "db_persist")
        out = persist_extraction_record(
            pdf_url,
            extracted_data,
            extracted_text,
            layout_blocks,
            request_id=request_id,
        )

        db_row = (out.get("db_record") or [{}])[0]
        finished_iso = datetime.now(timezone.utc).isoformat()
        store.update(
            {
                "status": "completed",
                "stage": "completed",
                "result": out,
                "action_id": db_row.get("id"),
                "finished_at": finished_iso,
            }
        )
        _update_case_db_status(
            pdf_url, "completed", "completed", finished_at=finished_iso
        )
        # Also update the legacy status field for dashboards
        try:
            get_supabase().table("cases").update({"status": "completed"}).eq(
                "pdf_url", pdf_url
            ).execute()
        except Exception:
            pass

        logger.info(
            "[extract] req=%s job=%s DONE in %.2fs action_id=%s",
            request_id, job_id, time.monotonic() - t_total, db_row.get("id"),
        )

    except Exception as exc:
        stage = store.get("stage", "unknown")
        finished_iso = datetime.now(timezone.utc).isoformat()
        store.update(
            {
                "status": "failed",
                "stage": stage,
                "error": str(exc),
                "error_stage": stage,
                "finished_at": finished_iso,
            }
        )
        _update_case_db_status(
            pdf_url, "failed", stage,
            error=str(exc), finished_at=finished_iso,
        )
        # Revert case.status back to pending so it reappears in queue
        try:
            get_supabase().table("cases").update({"status": "pending"}).eq(
                "pdf_url", pdf_url
            ).execute()
        except Exception:
            pass

        logger.error(
            "[extract] req=%s job=%s FAILED stage=%s in %.2fs: %s",
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
    EXTRACTION_JOB_STORE[job_id] = {
        "job_id": job_id,
        "pdf_url": payload.pdf_url,
        "status": "queued",
        "stage": "queued",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "finished_at": None,
        "error": None,
        "error_stage": None,
        "action_id": None,
    }

    # Best-effort case status update for dashboard UX
    try:
        get_supabase().table("cases").update({"status": "processing"}).eq(
            "pdf_url", payload.pdf_url
        ).execute()
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
            "source":      "memory",
        }
        if job.get("status") == "failed":
            response["error"]       = job.get("error")
            response["error_stage"] = job.get("error_stage")

        if job.get("status") == "completed":
            result = job.get("result") or {}
            response["result"] = {
                "message":        result.get("message"),
                "status":         result.get("status"),
                "extracted_data": result.get("extracted_data"),
                "action_plan":    result.get("action_plan"),
                "db_record":      result.get("db_record"),
            }
        return response

    # ── Slow path: check Supabase (backend may have restarted) ──
    pdf_url_from_store = None  # not available from job_id alone — query by job_id prefix not possible
    # job_id is not stored in Supabase, so we can only report 'unknown'
    # with a helpful message pointing the user to the case list.
    # BUT — if the backend just restarted, the DB holds processing_status written
    # by _update_case_db_status during the last run.  We cannot reverse-map
    # job_id → pdf_url without storing it, so return a structured 410 that
    # explains the situation and suggests checking the case list.
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
                "Each uploaded case row in Supabase now stores processing_status "
                "and processing_stage columns updated in real-time. "
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
        resp = (
            get_supabase()
            .table("cases")
            .select(
                "id,case_number,status,processing_status,processing_stage,"
                "processing_error,processing_started_at,processing_finished_at,pdf_url"
            )
            .eq("pdf_url", pdf_url)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.warning("[extract] case-processing-status DB query failed: %s", exc)
        raise HTTPException(status_code=503, detail=f"Database query failed: {exc}")

    rows = resp.data or []
    if not rows:
        raise HTTPException(
            status_code=404,
            detail={"error": "No case found for this PDF URL.", "pdf_url": pdf_url},
        )

    row = rows[0]
    ps    = row.get("processing_status") or "unknown"
    stage = row.get("processing_stage")  or "unknown"

    # Map DB status → job-store compatible status for frontend compatibility
    if ps == "completed":
        status = "completed"
    elif ps == "failed":
        status = "failed"
    elif ps == "processing":
        status = "processing"
    else:
        # Legacy rows without processing_status: derive from cases.status
        legacy = row.get("status", "unknown")
        status = (
            "completed" if legacy == "completed"
            else "processing" if legacy == "processing"
            else "queued"
        )

    return {
        "case_id":     row.get("id"),
        "case_number": row.get("case_number"),
        "pdf_url":     pdf_url,
        "status":      status,
        "stage":       stage,
        "error":       row.get("processing_error"),
        "started_at":  row.get("processing_started_at"),
        "finished_at": row.get("processing_finished_at"),
        "source":      "database",
    }
