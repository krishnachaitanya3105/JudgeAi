"""
Upload Router — POST /upload-pdf
──────────────────────────────────────────────────
Accepts a PDF file, stores it in Supabase Storage
(court-judgments bucket), and saves metadata to the
`cases` table.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from backend.config import get_supabase, SUPABASE_URL, SUPABASE_STORAGE_BUCKET

router = APIRouter()


@router.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    uploaded_by: str = Form(default="system"),
):
    """
    Upload a court judgment PDF to Supabase Storage and
    persist metadata into the `cases` table.

    Returns the public URL and case metadata.
    """

    # ── Validate file type ───────────────────────
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted.",
        )

    supabase = get_supabase()

    # ── Read file bytes ──────────────────────────
    file_bytes = await file.read()
    file_id = uuid.uuid4().hex[:12]
    storage_path = f"uploads/{file_id}_{file.filename}"

    # ── Upload to Supabase Storage ───────────────
    try:
        supabase.storage.from_(SUPABASE_STORAGE_BUCKET).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": "application/pdf"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Storage upload failed: {str(e)}",
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
    }

    try:
        result = supabase.table("cases").insert(metadata).execute()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database insert failed: {str(e)}",
        )

    return {
        "message": "PDF uploaded successfully",
        "case_number": case_number,
        "pdf_url": pdf_url,
        "metadata": metadata,
        "db_record": result.data,
    }
