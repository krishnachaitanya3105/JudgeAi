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
import json
import logging
import math
import time
from datetime import date, datetime, timezone
from decimal import Decimal
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


def _json_safe(value: Any) -> Any:
    """Recursively coerce arbitrary Python objects into JSON-safe values."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Decimal):
        return float(value) if value.is_finite() else None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _ensure_json_serializable(value: Any, *, label: str) -> Any:
    safe = _json_safe(value)
    try:
        json.dumps(safe, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} is not JSON serializable: {exc}") from exc
    return safe


def _execute_supabase(
    request_id: str,
    action: str,
    operation,
    *,
    payload_preview: Optional[Dict[str, Any]] = None,
):
    started = time.monotonic()
    if payload_preview is not None:
        logger.info(
            "[pipeline] req=%s supabase=%s before payload=%s",
            request_id,
            action,
            json.dumps(_json_safe(payload_preview), ensure_ascii=False)[:800],
        )
    else:
        logger.info("[pipeline] req=%s supabase=%s before", request_id, action)

    try:
        result = operation()
    except Exception as exc:
        logger.error(
            "[pipeline] req=%s supabase=%s fail elapsed=%.2fs err=%s",
            request_id,
            action,
            time.monotonic() - started,
            str(exc)[:300],
            exc_info=True,
        )
        raise

    rows = getattr(result, "data", None)
    row_count = len(rows) if isinstance(rows, list) else (1 if rows else 0)
    logger.info(
        "[pipeline] req=%s supabase=%s after elapsed=%.2fs rows=%s",
        request_id,
        action,
        time.monotonic() - started,
        row_count,
    )
    return result


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


def build_extraction_artifacts(
    pdf_url: str,
    extracted_data: Dict[str, Any],
    extracted_text: str,
    *,
    request_id: str = "n/a",
) -> Dict[str, Any]:
    from backend.utils.date_sanitize import coerce_pg_date, sanitize_action_plan_date_fields

    logger.info(
        "ANALYTICS_GENERATED request_id=%s pdf_url=%s payload_chars=%d",
        request_id,
        pdf_url[:120],
        len(extracted_text or ""),
    )

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

    safe_action_plan = _ensure_json_serializable(action_plan, label="action_plan")
    safe_reasoning = _ensure_json_serializable(reasoning, label="action_plan_reasoning")
    safe_extracted_data = _ensure_json_serializable(extracted_data, label="extracted_data")

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
        "action_plan": safe_action_plan,
        "action_plan_reasoning": safe_reasoning,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    return {
        "record": record,
        "safe_action_plan": safe_action_plan,
        "safe_reasoning": safe_reasoning,
        "safe_extracted_data": safe_extracted_data,
    }


def insert_extraction_record(
    record: Dict[str, Any],
    *,
    request_id: str = "n/a",
):
    logger.info(
        "DB_PERSIST_STARTED request_id=%s case_number=%s pdf_url=%s",
        request_id,
        record.get("case_number"),
        str(record.get("pdf_url", ""))[:120],
    )
    t = time.monotonic()
    supabase = get_supabase()
    try:
        result = _execute_supabase(
            request_id,
            "insert_extracted_actions",
            lambda: supabase.table("extracted_actions").insert(record).execute(),
            payload_preview={
                "case_number": record["case_number"],
                "pdf_url": record["pdf_url"],
                "department": record["department"],
                "deadline": record["deadline"],
                "status": record["status"],
            },
        )
    except Exception as exc:
        _log_stage(request_id, "db_insert", time.monotonic() - t, False, str(exc)[:120])
        raise ValueError(f"Database insert failed: {exc}") from exc
    _log_stage(request_id, "db_insert", time.monotonic() - t, True)
    logger.info(
        "DB_PERSIST_COMPLETED request_id=%s case_number=%s rows=%s",
        request_id,
        record.get("case_number"),
        len(result.data or []),
    )
    return result


def persist_extraction_record(
    pdf_url: str,
    extracted_data: Dict[str, Any],
    extracted_text: str,
    layout_blocks: list,
    request_id: str = "n/a",
    include_secondary_updates: bool = True,
) -> Dict[str, Any]:
    """
    Insert extracted_actions row and enrich linked case row.
    Secondary updates (embedding, layout_blocks) are best-effort.
    """
    artifacts = build_extraction_artifacts(
        pdf_url,
        extracted_data,
        extracted_text,
        request_id=request_id,
    )
    record = artifacts["record"]
    safe_action_plan = artifacts["safe_action_plan"]
    safe_reasoning = artifacts["safe_reasoning"]
    safe_extracted_data = artifacts["safe_extracted_data"]
    result = insert_extraction_record(record, request_id=request_id)
    supabase = get_supabase()

    # ── Stage 5: Secondary updates (best-effort, non-blocking) ─
    if include_secondary_updates:
        run_secondary_case_updates(
            pdf_url=pdf_url,
            extracted_text=extracted_text,
            layout_blocks=layout_blocks,
            request_id=request_id,
            supabase=supabase,
        )

    return {
        "message": "Extraction completed successfully",
        "extracted_data": safe_extracted_data,
        "action_plan": safe_action_plan,
        "action_plan_reasoning": safe_reasoning,
        "status": record["status"],
        "db_record": result.data,
    }


def run_secondary_case_updates(
    pdf_url: str,
    extracted_text: str,
    layout_blocks: list,
    request_id: str,
    supabase=None,
) -> None:
    """
    Embedding + layout_blocks updates are secondary; failures must not
    crash the main extraction result.  Run them inline (no extra thread)
    to avoid spawning threads on an already-strained Render process.
    """
    supabase = supabase or get_supabase()
    safe_layout_blocks = _ensure_json_serializable(layout_blocks, label="layout_blocks")

    logger.info("EMBEDDING_STARTED request_id=%s pdf_url=%s", request_id, pdf_url[:120])
    # Embedding
    t = time.monotonic()
    try:
        # Truncated to 3000 chars — MiniLM only uses ~512 tokens anyway
        vec = generate_embedding(extracted_text[:3000])
        _execute_supabase(
            request_id,
            "update_case_embedding",
            lambda: supabase.table("cases").update({"embedding": vec}).eq("pdf_url", pdf_url).execute(),
            payload_preview={
                "pdf_url": pdf_url,
                "embedding_dimensions": len(vec) if isinstance(vec, list) else None,
            },
        )
        _log_stage(request_id, "embedding_update", time.monotonic() - t, True)
        logger.info("EMBEDDING_COMPLETED request_id=%s pdf_url=%s", request_id, pdf_url[:120])
    except Exception as exc:
        _log_stage(request_id, "embedding_update", time.monotonic() - t, False, str(exc)[:80])
    finally:
        gc.collect()

    logger.info("DB_PERSIST_STARTED request_id=%s stage=layout_blocks pdf_url=%s", request_id, pdf_url[:120])
    # Layout blocks
    t = time.monotonic()
    try:
        _execute_supabase(
            request_id,
            "update_case_layout_blocks",
            lambda: supabase.table("cases").update({"layout_blocks": safe_layout_blocks}).eq("pdf_url", pdf_url).execute(),
            payload_preview={
                "pdf_url": pdf_url,
                "layout_blocks_count": len(safe_layout_blocks) if isinstance(safe_layout_blocks, list) else None,
            },
        )
        _log_stage(request_id, "layout_blocks_update", time.monotonic() - t, True)
        logger.info("DB_PERSIST_COMPLETED request_id=%s stage=layout_blocks pdf_url=%s", request_id, pdf_url[:120])
    except Exception as exc:
        _log_stage(request_id, "layout_blocks_update", time.monotonic() - t, False, str(exc)[:80])
