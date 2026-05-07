"""
Upload Router — POST /upload-pdf
──────────────────────────────────────────────────
Accepts a PDF file, stores it in Supabase Storage
(court-judgments bucket), and saves metadata to the
`cases` table.
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from backend.config import get_supabase, SUPABASE_URL, SUPABASE_STORAGE_BUCKET

router = APIRouter()
logger = logging.getLogger("judgeai.upload")


@router.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    uploaded_by: str = Form(default="system"),
):
    """
    Upload a court judgment PDF to Supabase Storage and
    persist metadata into the `cases` table.

    Returns the public URL and case metadata.
    
    Error handling:
      - 400: Invalid file type
      - 413: File too large
      - 500: Storage or database errors
    """

    # ── Validate file type ───────────────────────
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted.",
        )
    logger.info("UPLOAD_RECEIVED filename=%s uploaded_by=%s", file.filename, uploaded_by)

    # ── Validate file size (50 MB limit) ─────────
    max_size = 50 * 1024 * 1024  # 50 MB
    if file.size and file.size > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {max_size / 1024 / 1024:.0f} MB",
        )

    supabase = get_supabase()

    # ── Read file bytes ──────────────────────────
    try:
        file_bytes = await file.read()
    except Exception as e:
        logger.error("[upload] File read failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=f"Could not read file: {str(e)[:100]}",
        )

    # Validate it's actually a PDF
    if not file_bytes.startswith(b"%PDF"):
        raise HTTPException(
            status_code=400,
            detail="File is not a valid PDF. Please check the file and try again.",
        )

    file_id = uuid.uuid4().hex[:12]
    storage_path = f"uploads/{file_id}_{file.filename}"

    # ── Upload to Supabase Storage ───────────────
    try:
        supabase.storage.from_(SUPABASE_STORAGE_BUCKET).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": "application/pdf"},
        )
        logger.info("[upload] Stored PDF: %s (%d bytes)", storage_path, len(file_bytes))
    except Exception as e:
        logger.error("[upload] Storage upload failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Storage upload failed: {str(e)[:200]}",
        )

    # ── Build public URL ─────────────────────────
    pdf_url = (
        f"{SUPABASE_URL}/storage/v1/object/public/"
        f"{SUPABASE_STORAGE_BUCKET}/{storage_path}"
    )

    # ── Generate a temporary case number ─────────
    case_number = f"CASE-{file_id.upper()}"

    # ── Save metadata to `cases` table ───────────
    metadata = {
        "case_number": case_number,
        "pdf_url": pdf_url,
        "uploaded_by": uploaded_by,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
        "processing_status": None,
        "processing_stage": None,
    }

    try:
        result = supabase.table("cases").insert(metadata).execute()
        logger.info("[upload] Case created: %s pdf_url=%s", case_number, pdf_url[:80])
    except Exception as e:
        logger.error("[upload] Database insert failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Database insert failed: {str(e)[:200]}",
        )

    return {
        "message": "PDF uploaded successfully",
        "case_number": case_number,
        "pdf_url": pdf_url,
        "metadata": metadata,
        "db_record": result.data,
    }
