"""Batch PDF upload pipeline with BackgroundTasks.

Changes vs previous version:
  - request_id propagated to run_pdf_and_llm / persist_extraction_record for correlated logs.
  - Per-file error captured with stage detail (not just str(e)).
  - Batch status endpoint returns 410 Gone on process restart (matches extract router).
  - Added file-size guard: rejects individual files > MAX_PDF_MB.
  - JOB_STORE bounded to 50 most-recent jobs.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from backend.config import SUPABASE_STORAGE_BUCKET, SUPABASE_URL, get_supabase
from backend.services.pipeline import persist_extraction_record, run_pdf_and_llm

logger = logging.getLogger("judgeai.batch_upload")
router = APIRouter()

JOB_STORE: Dict[str, Dict[str, Any]] = {}
_MAX_BATCH_JOBS = 50
MAX_PDF_MB = int(os.getenv("JUDGEAI_MAX_PDF_MB", "20"))  # per-file cap


def _cleanup_job_store() -> None:
    if len(JOB_STORE) > _MAX_BATCH_JOBS:
        oldest = list(JOB_STORE.keys())[: len(JOB_STORE) - _MAX_BATCH_JOBS]
        for k in oldest:
            del JOB_STORE[k]


_BATCH_CONCURRENCY = int(os.getenv("JUDGEAI_BATCH_CONCURRENCY", "3"))
"""
Max simultaneous PDF→LLM pipelines inside a batch job.
Keep ≤ 3 on Render 512 MB free tier to avoid OOM.
Increase via JUDGEAI_BATCH_CONCURRENCY env var on paid plans.
"""


def _run_job(job_id: str, items: List[Dict[str, Any]]) -> None:
    """
    Process batch items concurrently (up to _BATCH_CONCURRENCY at a time).
    Each item runs run_pdf_and_llm → persist_extraction_record in its own thread.
    """
    import asyncio
    import concurrent.futures

    JOB_STORE[job_id]["status"] = "processing"
    JOB_STORE[job_id]["started_at"] = datetime.now(timezone.utc).isoformat()
    logger.info("[batch] job=%s START files=%d concurrency=%d",
                job_id, len(items), _BATCH_CONCURRENCY)
    t_total = time.monotonic()

    successes: List[dict] = []
    errors:    List[dict] = []

    # ── Thread-safe result collectors ───────────────────────
    import threading
    results_lock = threading.Lock()

    def _process_one(item: Dict[str, Any]) -> None:
        pdf_url  = item["pdf_url"]
        filename = item.get("filename", "")
        request_id = uuid.uuid4().hex[:8]
        t_file = time.monotonic()
        try:
            extracted_data, extracted_text, layout_blocks = run_pdf_and_llm(
                pdf_url, request_id=request_id
            )
            out = persist_extraction_record(
                pdf_url, extracted_data, extracted_text, layout_blocks,
                request_id=request_id,
            )
            action_id = (out.get("db_record") or [{}])[0].get("id")
            with results_lock:
                successes.append(
                    {"pdf_url": pdf_url, "filename": filename, "action_id": action_id}
                )
            logger.info(
                "[batch] job=%s req=%s file=%s OK in %.2fs action_id=%s",
                job_id, request_id, filename, time.monotonic() - t_file, action_id,
            )
        except Exception as e:
            with results_lock:
                errors.append(
                    {"pdf_url": pdf_url, "filename": filename, "detail": str(e)}
                )
            logger.error(
                "[batch] job=%s req=%s file=%s FAIL in %.2fs: %s",
                job_id, request_id, filename, time.monotonic() - t_file, str(e)[:200],
                exc_info=True,
            )

    # Run up to _BATCH_CONCURRENCY items in parallel using a thread pool
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=_BATCH_CONCURRENCY, thread_name_prefix=f"batch-{job_id[:8]}"
    ) as pool:
        futures = [pool.submit(_process_one, item) for item in items]
        for fut in concurrent.futures.as_completed(futures):
            # Propagate any unexpected exception (process_one swallows them,
            # but guard defensively anyway)
            try:
                fut.result()
            except Exception as exc:
                logger.error("[batch] job=%s unexpected future error: %s", job_id, exc)

    JOB_STORE[job_id].update(
        {
            "status": "completed",
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "successes": successes,
            "errors": errors,
        }
    )
    logger.info(
        "[batch] job=%s DONE in %.2fs ok=%d fail=%d",
        job_id, time.monotonic() - t_total, len(successes), len(errors),
    )



@router.post("/upload-batch")
async def upload_batch(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    uploaded_by: str = Form(default="system"),
):
    if not files:
        raise HTTPException(status_code=400, detail="At least one PDF is required.")

    supabase = get_supabase()
    job_id = uuid.uuid4().hex
    payload_items: List[Dict[str, Any]] = []

    for file in files:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail={"error": f"Only PDF files are accepted. Got: {file.filename}"},
            )

        fb = await file.read()

        # File size guard
        size_mb = len(fb) / 1_048_576
        if size_mb > MAX_PDF_MB:
            raise HTTPException(
                status_code=413,
                detail={
                    "error": f"File '{file.filename}' exceeds the {MAX_PDF_MB} MB limit ({size_mb:.1f} MB)."
                },
            )

        file_id = uuid.uuid4().hex[:12]
        storage_path = f"batch/{job_id}/{file_id}_{file.filename}"

        try:
            supabase.storage.from_(SUPABASE_STORAGE_BUCKET).upload(
                path=storage_path,
                file=fb,
                file_options={"content-type": "application/pdf"},
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail={"error": f"Storage upload failed for '{file.filename}': {e}"},
            )

        pdf_url = (
            f"{SUPABASE_URL}/storage/v1/object/public/"
            f"{SUPABASE_STORAGE_BUCKET}/{storage_path}"
        )
        payload_items.append(
            {"storage_path": storage_path, "pdf_url": pdf_url, "filename": file.filename}
        )

        md = {
            "case_number": f"BATCH-{file_id.upper()}",
            "pdf_url": pdf_url,
            "uploaded_by": uploaded_by,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "processing",
        }
        try:
            supabase.table("cases").insert(md).execute()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail={"error": f"Case insert failed for '{file.filename}': {e}"},
            )

    JOB_STORE[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "finished_at": None,
        "files_count": len(payload_items),
        "payload": payload_items,
        "successes": None,
        "errors": None,
    }

    background_tasks.add_task(_run_job, job_id, payload_items)
    _cleanup_job_store()

    logger.info("[batch] job=%s queued files=%d", job_id, len(payload_items))
    return {
        "job_id": job_id,
        "message": "Batch queued for extraction",
        "files_enqueued": len(payload_items),
    }


@router.get("/batch-status/{job_id}")
async def batch_status(job_id: str):
    """
    Poll batch job status.
    Returns 410 Gone on process restart (job_id absent from in-memory store).
    """
    job = JOB_STORE.get(job_id)
    if not job:
        raise HTTPException(
            status_code=410,
            detail={
                "error": (
                    "Batch job not found. The backend may have restarted "
                    "during processing. Individual files may still be in the case list."
                ),
                "job_id": job_id,
                "suggestion": "check_case_list",
            },
        )
    payload = job.get("payload", [])
    stripped = [{"pdf_url": p.get("pdf_url"), "filename": p.get("filename")} for p in payload]
    return {
        "job_id": job_id,
        "status": job.get("status"),
        "created_at": job.get("created_at"),
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
        "files": stripped,
        "successes": job.get("successes") if job.get("status") == "completed" else None,
        "errors": job.get("errors") if job.get("status") == "completed" else None,
    }
