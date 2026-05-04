"""Batch PDF upload pipeline with BackgroundTasks."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from backend.config import SUPABASE_URL, get_supabase, SUPABASE_STORAGE_BUCKET
from backend.services.pipeline import persist_extraction_record, run_pdf_and_llm

router = APIRouter()

JOB_STORE: Dict[str, Dict[str, Any]] = {}


def _run_job(job_id: str, items: List[Dict[str, Any]]) -> None:
    JOB_STORE[job_id]["status"] = "processing"
    JOB_STORE[job_id]["started_at"] = datetime.now(timezone.utc).isoformat()

    successes = []
    errors = []
    supabase = get_supabase()

    for item in items:
        path = item["storage_path"]
        pdf_url = item["pdf_url"]
        try:
            extracted_data, extracted_text, layout_blocks = run_pdf_and_llm(pdf_url)
            out = persist_extraction_record(pdf_url, extracted_data, extracted_text, layout_blocks)
            successes.append({"pdf_url": pdf_url, "action_id": (out.get("db_record") or [{}])[0].get("id")})
        except Exception as e:
            errors.append({"pdf_url": pdf_url, "detail": str(e)})

    JOB_STORE[job_id]["status"] = "completed"
    JOB_STORE[job_id]["finished_at"] = datetime.now(timezone.utc).isoformat()
    JOB_STORE[job_id]["successes"] = successes
    JOB_STORE[job_id]["errors"] = errors


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
            raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

        fb = await file.read()
        file_id = uuid.uuid4().hex[:12]
        storage_path = f"batch/{job_id}/{file_id}_{file.filename}"

        try:
            supabase.storage.from_(SUPABASE_STORAGE_BUCKET).upload(
                path=storage_path,
                file=fb,
                file_options={"content-type": "application/pdf"},
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Storage upload failed: {e}")

        pdf_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}/{storage_path}"
        payload_items.append(
            {
                "storage_path": storage_path,
                "pdf_url": pdf_url,
                "filename": file.filename,
            }
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
            raise HTTPException(status_code=500, detail=f"Case insert failed: {e}")

    JOB_STORE[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files_count": len(payload_items),
        "payload": payload_items,
    }

    background_tasks.add_task(_run_job, job_id, payload_items)

    return {
        "job_id": job_id,
        "message": "Batch queued for extraction",
        "files_enqueued": len(payload_items),
    }


@router.get("/batch-status/{job_id}")
async def batch_status(job_id: str):
    job = JOB_STORE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown job id")
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
