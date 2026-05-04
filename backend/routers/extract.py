"""
Extract Router — synchronous and asynchronous extraction flows.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from backend.config import get_supabase
from backend.services.pipeline import persist_extraction_record, run_pdf_and_llm

router = APIRouter()
EXTRACTION_JOB_STORE: Dict[str, Dict[str, Any]] = {}


class ExtractRequest(BaseModel):
    pdf_url: str


def _run_single_extraction_job(job_id: str, pdf_url: str) -> None:
    EXTRACTION_JOB_STORE[job_id]["status"] = "processing"
    EXTRACTION_JOB_STORE[job_id]["started_at"] = datetime.now(timezone.utc).isoformat()
    try:
        extracted_data, extracted_text, layout_blocks = run_pdf_and_llm(pdf_url)
        out = persist_extraction_record(
            pdf_url,
            extracted_data,
            extracted_text,
            layout_blocks,
        )
        db_row = (out.get("db_record") or [{}])[0]
        EXTRACTION_JOB_STORE[job_id]["status"] = "completed"
        EXTRACTION_JOB_STORE[job_id]["result"] = out
        EXTRACTION_JOB_STORE[job_id]["action_id"] = db_row.get("id")
    except Exception as e:
        EXTRACTION_JOB_STORE[job_id]["status"] = "failed"
        EXTRACTION_JOB_STORE[job_id]["error"] = str(e)
    finally:
        EXTRACTION_JOB_STORE[job_id]["finished_at"] = datetime.now(timezone.utc).isoformat()
        # best-effort case status sync
        try:
            supabase = get_supabase()
            next_status = "completed" if EXTRACTION_JOB_STORE[job_id]["status"] == "completed" else "pending"
            supabase.table("cases").update({"status": next_status}).eq("pdf_url", pdf_url).execute()
        except Exception:
            pass


@router.post("/extract-actions")
async def extract_actions(payload: ExtractRequest):
    try:
        extracted_data, extracted_text, layout_blocks = run_pdf_and_llm(payload.pdf_url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        return persist_extraction_record(
            payload.pdf_url,
            extracted_data,
            extracted_text,
            layout_blocks,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database insert failed: {str(e)}")


@router.post("/extract-actions-async")
async def extract_actions_async(payload: ExtractRequest, background_tasks: BackgroundTasks):
    """Queue single-file extraction so upload flow returns immediately."""
    job_id = uuid.uuid4().hex
    EXTRACTION_JOB_STORE[job_id] = {
        "job_id": job_id,
        "pdf_url": payload.pdf_url,
        "status": "queued",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    # best-effort case status update for dashboard UX
    try:
        get_supabase().table("cases").update({"status": "processing"}).eq("pdf_url", payload.pdf_url).execute()
    except Exception:
        pass

    background_tasks.add_task(_run_single_extraction_job, job_id, payload.pdf_url)
    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Extraction queued",
        "pdf_url": payload.pdf_url,
    }


@router.get("/extract-actions-status/{job_id}")
async def extract_actions_status(job_id: str):
    job = EXTRACTION_JOB_STORE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown extraction job id")
    return {
        "job_id": job_id,
        "status": job.get("status"),
        "created_at": job.get("created_at"),
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
        "pdf_url": job.get("pdf_url"),
        "action_id": job.get("action_id"),
        "error": job.get("error"),
        "result": job.get("result") if job.get("status") == "completed" else None,
    }
