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

def _run_single_extraction_job(job_id: str, pdf_url: str) -> None:
    """
    Executed by FastAPI BackgroundTasks in a thread.
    Updates EXTRACTION_JOB_STORE at every stage so polling has granularity.
    """
    request_id = job_id[:8]          # short alias for logs
    store = EXTRACTION_JOB_STORE[job_id]

    store["status"] = "processing"
    store["stage"] = "pdf_extraction"
    store["started_at"] = datetime.now(timezone.utc).isoformat()

    logger.info(
        "[extract] req=%s job=%s START url=%s", request_id, job_id, pdf_url[:80]
    )
    t_total = time.monotonic()

    try:
        # ── Stage 1: PDF → text ──────────────────────────────
        store["stage"] = "pdf_extraction"
        extracted_data, extracted_text, layout_blocks = run_pdf_and_llm(
            pdf_url, request_id=request_id
        )

        # ── Stage 2: DB persist + secondary updates ──────────
        store["stage"] = "db_persist"
        out = persist_extraction_record(
            pdf_url,
            extracted_data,
            extracted_text,
            layout_blocks,
            request_id=request_id,
        )

        db_row = (out.get("db_record") or [{}])[0]
        store.update(
            {
                "status": "completed",
                "stage": "completed",
                "result": out,
                "action_id": db_row.get("id"),
            }
        )
        logger.info(
            "[extract] req=%s job=%s DONE in %.2fs action_id=%s",
            request_id, job_id, time.monotonic() - t_total, db_row.get("id"),
        )

    except Exception as exc:
        stage = store.get("stage", "unknown")
        store.update(
            {
                "status": "failed",
                "stage": stage,
                "error": str(exc),
                "error_stage": stage,
            }
        )
        logger.error(
            "[extract] req=%s job=%s FAILED stage=%s in %.2fs: %s",
            request_id, job_id, stage, time.monotonic() - t_total, str(exc)[:200],
            exc_info=True,
        )

    finally:
        store["finished_at"] = datetime.now(timezone.utc).isoformat()
        # Best-effort case status sync
        try:
            supabase = get_supabase()
            next_status = (
                "completed" if store["status"] == "completed" else "pending"
            )
            supabase.table("cases").update({"status": next_status}).eq(
                "pdf_url", pdf_url
            ).execute()
        except Exception as sync_exc:
            logger.warning(
                "[extract] req=%s case status sync failed: %s", request_id, sync_exc
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

    Returns 410 Gone (not 404) when the job_id is unknown — this
    typically means the backend process restarted and lost in-memory state.
    The frontend should handle 410 by stopping polling and showing an
    appropriate 'process restarted' message rather than a generic error.
    """
    job = EXTRACTION_JOB_STORE.get(job_id)
    if not job:
        raise HTTPException(
            status_code=410,
            detail={
                "error": (
                    "Extraction job not found. The backend may have restarted "
                    "during processing. Please check the case list — your document "
                    "may have been partially processed."
                ),
                "job_id": job_id,
                "suggestion": "check_case_list",
            },
        )

    response: Dict[str, Any] = {
        "job_id": job_id,
        "status": job.get("status"),
        "stage": job.get("stage"),
        "created_at": job.get("created_at"),
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
        "pdf_url": job.get("pdf_url"),
        "action_id": job.get("action_id"),
    }

    if job.get("status") == "failed":
        response["error"] = job.get("error")
        response["error_stage"] = job.get("error_stage")

    if job.get("status") == "completed":
        # Return only lightweight summary; full result is large
        result = job.get("result") or {}
        response["result"] = {
            "message": result.get("message"),
            "status": result.get("status"),
            "extracted_data": result.get("extracted_data"),
            "action_plan": result.get("action_plan"),
            "db_record": result.get("db_record"),
        }

    return response
