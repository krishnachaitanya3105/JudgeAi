"""
Audit Logger — Reusable Logging Function
──────────────────────────────────────────────────
Centralized function to log audit events into the
audit_logs table for compliance and tracking.
"""

from datetime import datetime, timezone
from typing import Optional
from backend.config import get_supabase


def log_audit_event(
    case_id: str,
    action_type: str,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    edited_by: str = "system",
    notes: Optional[str] = None,
) -> dict:
    """
    Log an audit event to the audit_logs table.

    Args:
        case_id: The case or action ID being modified.
        action_type: Type of action (e.g., 'status_change', 'field_edit', 'rejection').
        old_value: Previous value (if applicable).
        new_value: New value (if applicable).
        edited_by: User/system identifier who made the change.
        notes: Additional context or notes about the change.

    Returns:
        Dict containing the inserted record.

    Raises:
        Exception: If the database insert fails.
    """
    supabase = get_supabase()

    audit_record = {
        "case_id": case_id,
        "action_type": action_type,
        "old_value": old_value,
        "new_value": new_value,
        "edited_by": edited_by,
        "notes": notes,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        result = supabase.table("audit_logs").insert(audit_record).execute()
        return result.data[0] if result.data else audit_record
    except Exception as e:
        print(f"Error logging audit event: {str(e)}")
        raise


def get_audit_log_for_case(case_id: str) -> list:
    """
    Retrieve all audit log entries for a specific case.

    Args:
        case_id: The case ID to retrieve logs for.

    Returns:
        List of audit log records, ordered by timestamp descending.
    """
    supabase = get_supabase()

    try:
        result = (
            supabase.table("audit_logs")
            .select("*")
            .eq("case_id", case_id)
            .order("timestamp", desc=True)
            .execute()
        )
        return result.data if result.data else []
    except Exception as e:
        print(f"Error retrieving audit logs: {str(e)}")
        return []


def get_audit_log_stats(start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict:
    """
    Get statistics about audit logs (e.g., for dashboard).

    Args:
        start_date: ISO 8601 datetime (optional).
        end_date: ISO 8601 datetime (optional).

    Returns:
        Dict with stats like total_actions, by_type, by_editor.
    """
    supabase = get_supabase()

    try:
        query = supabase.table("audit_logs").select("*")

        if start_date:
            query = query.gte("timestamp", start_date)
        if end_date:
            query = query.lte("timestamp", end_date)

        result = query.execute()
        logs = result.data if result.data else []

        # Aggregate stats
        stats = {
            "total_actions": len(logs),
            "by_action_type": {},
            "by_editor": {},
        }

        for log in logs:
            action_type = log.get("action_type", "unknown")
            edited_by = log.get("edited_by", "unknown")

            stats["by_action_type"][action_type] = stats["by_action_type"].get(action_type, 0) + 1
            stats["by_editor"][edited_by] = stats["by_editor"].get(edited_by, 0) + 1

        return stats
    except Exception as e:
        print(f"Error retrieving audit stats: {str(e)}")
        return {"total_actions": 0, "by_action_type": {}, "by_editor": {}}
