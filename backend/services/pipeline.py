"""
Shared extraction pipeline for extract-actions and demo flows.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Tuple

from backend.config import get_supabase
from backend.services.action_plan_generator import generate_action_plan
from backend.services.embedding_service import generate_embedding
from backend.services.llm_extractor import extract_judgment_actions
from backend.services.pdf_parser import extract_pdf_bundle_from_url
from backend.utils.date_sanitize import coerce_pg_date, sanitize_action_plan_date_fields

import concurrent.futures


def run_pdf_and_llm(pdf_url: str) -> Tuple[Dict[str, Any], str, list]:
    """Download PDF → text & blocks → LLM extraction."""
    extracted_text, layout_blocks = extract_pdf_bundle_from_url(pdf_url)
    if not extracted_text or len(extracted_text.strip()) < 20:
        raise ValueError("Could not extract meaningful text from the PDF.")
    extracted_data = extract_judgment_actions(extracted_text)
    return extracted_data, extracted_text, layout_blocks


def persist_extraction_record(
    pdf_url: str,
    extracted_data: Dict[str, Any],
    extracted_text: str,
    layout_blocks,
) -> Dict[str, Any]:
    """Insert extracted_actions row and enrich linked case row."""
    supabase = get_supabase()
    action_plan, reasoning = generate_action_plan(extracted_data, full_judgment_text=extracted_text)
    sanitize_action_plan_date_fields(action_plan)

    fused = reasoning.get(
        "final_action_plan_confidence",
        extracted_data.get("confidence_score") or 0,
    )

    deadline_val = coerce_pg_date(extracted_data.get("deadline"))
    if action_plan.get("compliance_deadline"):
        cd = coerce_pg_date(action_plan["compliance_deadline"])
        if cd:
            deadline_val = cd

    judgment_iso = coerce_pg_date(extracted_data.get("judgment_date"))

    record = {
        "case_number": extracted_data.get("case_number", "UNKNOWN"),
        "judgment_date": judgment_iso,
        "department": action_plan.get("department") or extracted_data.get("department"),
        "deadline": deadline_val,
        "directive": extracted_data.get("directive"),
        "confidence_score": float(fused),
        "source_sentence": extracted_data.get("source_sentence"),
        "pdf_url": pdf_url,
        "status": "pending",
        "action_plan": action_plan,
        "action_plan_reasoning": reasoning,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    result = supabase.table("extracted_actions").insert(record).execute()

    def _update_layout_blocks():
        try:
            supabase.table("cases").update({"layout_blocks": layout_blocks}).eq("pdf_url", pdf_url).execute()
        except Exception:
            pass

    def _update_embedding():
        try:
            vec = generate_embedding(extracted_text[:12000])
            supabase.table("cases").update({"embedding": vec}).eq("pdf_url", pdf_url).execute()
        except Exception:
            pass

    # Fire and forget secondary updates to reduce response latency
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(_update_layout_blocks)
        executor.submit(_update_embedding)

    return {
        "message": "Extraction completed successfully",
        "extracted_data": extracted_data,
        "action_plan": action_plan,
        "action_plan_reasoning": reasoning,
        "status": record["status"],
        "db_record": result.data,
    }
