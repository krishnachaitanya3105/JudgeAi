"""One-shot investor demo pipeline: extract → classify → fuse → auto-approve."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import get_supabase
from backend.services.pipeline import persist_extraction_record, run_pdf_and_llm

router = APIRouter()


class DemoRequest(BaseModel):
    pdf_url: str


@router.post("/demo-process")
async def demo_process(payload: DemoRequest):
    try:
        extracted_data, extracted_text, layout_blocks = run_pdf_and_llm(payload.pdf_url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        out = persist_extraction_record(
            payload.pdf_url,
            extracted_data,
            extracted_text,
            layout_blocks,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Persistence failed: {e}")

    rows = out.get("db_record") or []
    aid = rows[0].get("id") if rows else None
    if aid:
        supabase = get_supabase()
        supabase.table("extracted_actions").update(
            {"status": "approved", "updated_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", aid).execute()

    action_plan = out.get("action_plan") or {}

    return {
        "final_action_plan": action_plan,
        "action_plan_reasoning": out.get("action_plan_reasoning"),
        "extracted_data": out.get("extracted_data"),
        "auto_approved_action_id": aid,
        "message": "Demo pipeline finished (timeline, appeal, department, fusion, auto-approved)",
    }
