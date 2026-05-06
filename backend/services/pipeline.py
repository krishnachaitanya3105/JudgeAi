"""
Shared extraction pipeline for extract-actions and demo flows.

Every stage is logged with:
  - request_id (propagated from caller)
  - stage name
  - elapsed time
  - RSS memory usage
  - success/failure indicator

This lets Render logs pinpoint exactly which stage OOMs or times out.
"""

from __future__ import annotations

import gc
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from backend.config import get_supabase
from backend.services.action_plan_generator import generate_action_plan
from backend.services.embedding_service import generate_embedding
from backend.services.llm_extractor import extract_judgment_actions
from backend.services.pdf_parser import extract_pdf_bundle_from_url

logger = logging.getLogger("judgeai.pipeline")


def _rss_mb() -> float:
    try:
        import psutil, os as _os
        return psutil.Process(_os.getpid()).memory_info().rss / 1_048_576
    except Exception:
        return 0.0


def _log_stage(request_id: str, stage: str, elapsed: float, ok: bool, extra: str = "") -> None:
    status = "OK" if ok else "FAIL"
    logger.info(
        "[pipeline] req=%s stage=%-24s status=%s elapsed=%.2fs rss=%.1f MB %s",
        request_id, stage, status, elapsed, _rss_mb(), extra,
    )


def run_pdf_and_llm(
    pdf_url: str,
    request_id: str = "n/a",
) -> Tuple[Dict[str, Any], str, list]:
    """
    Download PDF → text & blocks → LLM extraction.

    Raises ValueError with a human-readable message on any failure.
    """
    pipeline_start = time.monotonic()
    logger.info(
        "[pipeline] req=%s START url=%s rss=%.1f MB",
        request_id, pdf_url[:80], _rss_mb(),
    )

    # ── Stage 1: PDF download + text extraction ───────────────
    t = time.monotonic()
    try:
        extracted_text, layout_blocks = extract_pdf_bundle_from_url(pdf_url)
    except Exception as exc:
        _log_stage(request_id, "pdf_extraction", time.monotonic() - t, False, str(exc)[:120])
        raise ValueError(f"PDF extraction failed: {exc}") from exc
    _log_stage(
        request_id, "pdf_extraction", time.monotonic() - t, True,
        f"chars={len(extracted_text)} blocks={len(layout_blocks)}",
    )

    if not extracted_text or len(extracted_text.strip()) < 20:
        raise ValueError(
            "Could not extract meaningful text from the PDF. "
            "The file may be corrupt, password-protected, or purely image-based."
        )

    # ── Stage 2: LLM extraction (Groq) ────────────────────────
    t = time.monotonic()
    try:
        extracted_data = extract_judgment_actions(extracted_text, request_id=request_id)
    except Exception as exc:
        _log_stage(request_id, "llm_extraction", time.monotonic() - t, False, str(exc)[:120])
        raise ValueError(f"AI analysis failed: {exc}") from exc
    _log_stage(
        request_id, "llm_extraction", time.monotonic() - t, True,
        f"case={extracted_data.get('case_number')} conf={extracted_data.get('confidence_score')}",
    )

    logger.info(
        "[pipeline] req=%s COMPLETE total=%.2fs rss=%.1f MB",
        request_id, time.monotonic() - pipeline_start, _rss_mb(),
    )
    return extracted_data, extracted_text, layout_blocks


def persist_extraction_record(
    pdf_url: str,
    extracted_data: Dict[str, Any],
    extracted_text: str,
    layout_blocks: list,
    request_id: str = "n/a",
) -> Dict[str, Any]:
    """
    Insert extracted_actions row and enrich linked case row.
    Secondary updates (embedding, layout_blocks) are best-effort.
    """
    from backend.utils.date_sanitize import coerce_pg_date, sanitize_action_plan_date_fields

    # ── Stage 3: Action plan generation ───────────────────────
    t = time.monotonic()
    try:
        action_plan, reasoning = generate_action_plan(
            extracted_data, full_judgment_text=extracted_text
        )
        sanitize_action_plan_date_fields(action_plan)
    except Exception as exc:
        _log_stage(request_id, "action_plan", time.monotonic() - t, False, str(exc)[:120])
        raise ValueError(f"Action plan generation failed: {exc}") from exc
    _log_stage(request_id, "action_plan", time.monotonic() - t, True)

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

    # ── Stage 4: Supabase insert ───────────────────────────────
    t = time.monotonic()
    supabase = get_supabase()
    try:
        result = supabase.table("extracted_actions").insert(record).execute()
    except Exception as exc:
        _log_stage(request_id, "db_insert", time.monotonic() - t, False, str(exc)[:120])
        raise ValueError(f"Database insert failed: {exc}") from exc
    _log_stage(request_id, "db_insert", time.monotonic() - t, True)

    # ── Stage 5: Secondary updates (best-effort, non-blocking) ─
    _run_secondary_updates(supabase, pdf_url, extracted_text, layout_blocks, request_id)

    return {
        "message": "Extraction completed successfully",
        "extracted_data": extracted_data,
        "action_plan": action_plan,
        "action_plan_reasoning": reasoning,
        "status": record["status"],
        "db_record": result.data,
    }


def _run_secondary_updates(
    supabase,
    pdf_url: str,
    extracted_text: str,
    layout_blocks: list,
    request_id: str,
) -> None:
    """
    Embedding + layout_blocks updates are secondary; failures must not
    crash the main extraction result.  Run them inline (no extra thread)
    to avoid spawning threads on an already-strained Render process.
    """
    # Embedding
    t = time.monotonic()
    try:
        # Truncated to 3000 chars — MiniLM only uses ~512 tokens anyway
        vec = generate_embedding(extracted_text[:3000])
        supabase.table("cases").update({"embedding": vec}).eq("pdf_url", pdf_url).execute()
        _log_stage(request_id, "embedding_update", time.monotonic() - t, True)
    except Exception as exc:
        _log_stage(request_id, "embedding_update", time.monotonic() - t, False, str(exc)[:80])
    finally:
        gc.collect()

    # Layout blocks
    t = time.monotonic()
    try:
        supabase.table("cases").update({"layout_blocks": layout_blocks}).eq("pdf_url", pdf_url).execute()
        _log_stage(request_id, "layout_blocks_update", time.monotonic() - t, True)
    except Exception as exc:
        _log_stage(request_id, "layout_blocks_update", time.monotonic() - t, False, str(exc)[:80])
