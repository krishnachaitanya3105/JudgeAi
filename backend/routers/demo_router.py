"""One-shot investor demo pipeline: extract → classify → fuse → auto-approve."""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import get_supabase
from backend.services.pipeline import persist_extraction_record, run_pdf_and_llm

logger = logging.getLogger("judgeai.demo")
router = APIRouter()


class DemoRequest(BaseModel):
    pdf_url: str


@router.post("/demo-process")
async def demo_process(payload: DemoRequest):
    request_id = uuid.uuid4().hex[:8]
    try:
        extracted_data, extracted_text, layout_blocks = run_pdf_and_llm(
            payload.pdf_url, request_id=request_id
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail={"error": str(e), "request_id": request_id})
    except Exception as e:
        logger.error("[demo] req=%s unexpected: %s", request_id, e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "request_id": request_id},
        )

    try:
        out = persist_extraction_record(
            payload.pdf_url, extracted_data, extracted_text, layout_blocks,
            request_id=request_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": f"Persistence failed: {e}", "request_id": request_id},
        )

    rows = out.get("db_record") or []
    aid = rows[0].get("id") if rows else None
    if aid:
        supabase = get_supabase()
        try:
            supabase.table("extracted_actions").update(
                {"status": "approved", "updated_at": datetime.now(timezone.utc).isoformat()}
            ).eq("id", aid).execute()
        except Exception as e:
            logger.warning("[demo] req=%s auto-approve failed: %s", request_id, e)

    return {
        "final_action_plan": out.get("action_plan") or {},
        "action_plan_reasoning": out.get("action_plan_reasoning"),
        "extracted_data": out.get("extracted_data"),
        "auto_approved_action_id": aid,
        "request_id": request_id,
        "message": "Demo pipeline finished (timeline, appeal, department, fusion, auto-approved)",
    }
