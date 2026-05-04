"""
Verification Router — Approve/Edit/Reject Actions
──────────────────────────────────────────────────
Endpoints to manage extracted actions:
  - POST /approve-action/{id}
  - POST /edit-action/{id}
  - POST /reject-action/{id}

Each modifies status and logs changes to audit_logs table.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel
from typing import Optional
import json

from backend.config import get_supabase
from backend.utils.audit_logger import log_audit_event
from backend.utils.date_sanitize import coerce_pg_date

router = APIRouter()


# ── Request Schemas ──────────────────────────────

class ApproveActionRequest(BaseModel):
    """Request to approve an action."""
    approved_by: str = "system"


class EditActionRequest(BaseModel):
    """Request to edit an action with human-verified values."""
    case_number: Optional[str] = None
    judgment_date: Optional[str] = None
    department: Optional[str] = None
    deadline: Optional[str] = None
    directive: Optional[str] = None
    confidence_score: Optional[float] = None
    edited_by: str = "system"


class RejectActionRequest(BaseModel):
    """Request to reject an action."""
    rejection_reason: str
    rejected_by: str = "system"


# ── Endpoints ────────────────────────────────────

@router.post("/approve-action/{action_id}")
async def approve_action(
    action_id: str = Path(..., description="ID of the extracted action"),
    payload: ApproveActionRequest = None,
):
    """
    Approve an extracted action.
    Updates status to 'approved' and logs the change in audit_logs.
    """
    if payload is None:
        payload = ApproveActionRequest()

    supabase = get_supabase()

    # Fetch the current record
    try:
        response = supabase.table("extracted_actions").select("*").eq("id", action_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Action not found")
        current_record = response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database fetch failed: {str(e)}")

    old_status = current_record.get("status")
    new_status = "approved"

    # Update the record
    try:
        update_data = {
            "status": new_status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        supabase.table("extracted_actions").update(update_data).eq("id", action_id).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database update failed: {str(e)}")

    # Log the change
    try:
        log_audit_event(
            case_id=action_id,
            action_type="status_change",
            old_value=old_status,
            new_value=new_status,
            edited_by=payload.approved_by,
        )
    except Exception as e:
        # Log but don't fail the entire operation
        pass

    return {
        "message": "Action approved successfully",
        "action_id": action_id,
        "status": new_status,
    }


@router.post("/edit-action/{action_id}")
async def edit_action(
    action_id: str = Path(..., description="ID of the extracted action"),
    payload: EditActionRequest = None,
):
    """
    Edit an extracted action with human-verified values.
    Updates relevant fields, changes status to 'edited', and logs changes.
    """
    if payload is None:
        payload = EditActionRequest()

    supabase = get_supabase()

    # Fetch the current record
    try:
        response = supabase.table("extracted_actions").select("*").eq("id", action_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Action not found")
        current_record = response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database fetch failed: {str(e)}")

    # Prepare update data
    update_data = {
        "status": "edited",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    jd_coerced = None
    dl_coerced = None

    # Only update fields that were provided
    if payload.case_number is not None:
        update_data["case_number"] = payload.case_number
    if payload.judgment_date is not None:
        jd_coerced = coerce_pg_date(payload.judgment_date)
        if payload.judgment_date not in (None, "") and str(payload.judgment_date).strip() and jd_coerced is None:
            raise HTTPException(
                status_code=422,
                detail="judgment_date must be a calendar date in YYYY-MM-DD (or a standard format we can parse).",
            )
        update_data["judgment_date"] = jd_coerced
    if payload.department is not None:
        update_data["department"] = payload.department
    if payload.deadline is not None:
        dl_coerced = coerce_pg_date(payload.deadline)
        if payload.deadline not in (None, "") and str(payload.deadline).strip() and dl_coerced is None:
            raise HTTPException(
                status_code=422,
                detail="deadline must be a calendar date in YYYY-MM-DD (not a descriptive phrase like '30 days').",
            )
        update_data["deadline"] = dl_coerced
    if payload.directive is not None:
        update_data["directive"] = payload.directive
    if payload.confidence_score is not None:
        update_data["confidence_score"] = payload.confidence_score

    # Persist the human-verified values for case-details history view
    human_verified_values = {
        k: v
        for k, v in {
            "case_number": payload.case_number,
            "judgment_date": jd_coerced,
            "department": payload.department,
            "deadline": dl_coerced,
            "directive": payload.directive,
            "confidence_score": payload.confidence_score,
        }.items()
        if v is not None
    }
    if human_verified_values:
        update_data["human_verified_values"] = human_verified_values

    # Update the record
    try:
        supabase.table("extracted_actions").update(update_data).eq("id", action_id).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database update failed: {str(e)}")

    # Log each field change
    try:
        changes = []
        if payload.case_number is not None and payload.case_number != current_record.get("case_number"):
            changes.append(("case_number", current_record.get("case_number"), payload.case_number))
        if payload.judgment_date is not None and jd_coerced != current_record.get("judgment_date"):
            changes.append(("judgment_date", current_record.get("judgment_date"), jd_coerced))
        if payload.department is not None and payload.department != current_record.get("department"):
            changes.append(("department", current_record.get("department"), payload.department))
        if payload.deadline is not None and dl_coerced != current_record.get("deadline"):
            changes.append(("deadline", current_record.get("deadline"), dl_coerced))
        if payload.directive is not None and payload.directive != current_record.get("directive"):
            changes.append(("directive", current_record.get("directive"), payload.directive))
        if payload.confidence_score is not None and payload.confidence_score != current_record.get("confidence_score"):
            changes.append(("confidence_score", current_record.get("confidence_score"), payload.confidence_score))

        for field_name, old_val, new_val in changes:
            log_audit_event(
                case_id=action_id,
                action_type="field_edit",
                old_value=str(old_val),
                new_value=str(new_val),
                edited_by=payload.edited_by,
            )
        if human_verified_values:
            log_audit_event(
                case_id=action_id,
                action_type="human_verification_snapshot",
                old_value=None,
                new_value=json.dumps(human_verified_values),
                edited_by=payload.edited_by,
            )
    except Exception as e:
        pass

    return {
        "message": "Action edited successfully",
        "action_id": action_id,
        "status": "edited",
        "updated_fields": list(update_data.keys()),
    }


@router.post("/reject-action/{action_id}")
async def reject_action(
    action_id: str = Path(..., description="ID of the extracted action"),
    payload: RejectActionRequest = None,
):
    """
    Reject an extracted action.
    Updates status to 'rejected', stores rejection reason, and logs the change.
    """
    if payload is None:
        raise HTTPException(status_code=422, detail="rejection_reason is required")

    supabase = get_supabase()

    # Fetch the current record
    try:
        response = supabase.table("extracted_actions").select("*").eq("id", action_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Action not found")
        current_record = response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database fetch failed: {str(e)}")

    old_status = current_record.get("status")
    new_status = "rejected"

    # Update the record
    try:
        update_data = {
            "status": new_status,
            "rejection_reason": payload.rejection_reason,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        supabase.table("extracted_actions").update(update_data).eq("id", action_id).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database update failed: {str(e)}")

    # Log the change
    try:
        log_audit_event(
            case_id=action_id,
            action_type="rejection",
            old_value=old_status,
            new_value=new_status,
            edited_by=payload.rejected_by,
            notes=payload.rejection_reason,
        )
    except Exception as e:
        pass

    return {
        "message": "Action rejected successfully",
        "action_id": action_id,
        "status": new_status,
        "rejection_reason": payload.rejection_reason,
    }
