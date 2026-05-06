"""
Deadline Countdown Helper
──────────────────────────────────────────────────
Utility to calculate remaining time until a deadline,
determine urgency level, and track overdue items.
"""

from datetime import datetime, timezone
from typing import Optional, Dict


def parse_deadline(deadline_str: Optional[str]) -> Optional[datetime]:
    """
    Parse a deadline string into a datetime object.
    Supports ISO 8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS).

    Args:
        deadline_str: ISO 8601 formatted deadline string.

    Returns:
        datetime object in UTC, or None if parsing fails.
    """
    if not deadline_str:
        return None

    try:
        # Try ISO format with time
        if "T" in deadline_str:
            return datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
        # Try ISO format without time (assume end of day)
        else:
            dt = datetime.fromisoformat(deadline_str)
            return dt.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def calculate_deadline_remaining(deadline_date: str) -> Dict:
    """
    Calculate remaining time until the deadline and determine urgency.

    Args:
        deadline_date: ISO 8601 formatted deadline string.

    Returns:
        Dict with keys:
            - days_remaining: int (negative if overdue)
            - is_overdue: bool
            - priority_level: str ("urgent" | "warning" | "normal")
            - hours_remaining: int
            - formatted_remaining: str (human-readable)

    Priority Logic:
        Urgent: < 3 days
        Warning: < 7 days
        Normal: >= 7 days
    """
    deadline_dt = parse_deadline(deadline_date)
    if not deadline_dt:
        return {
            "days_remaining": None,
            "is_overdue": None,
            "priority_level": "unknown",
            "hours_remaining": None,
            "formatted_remaining": "Invalid date",
        }

    now = datetime.now(timezone.utc)

    # Calculate differences
    time_diff = deadline_dt - now
    days_remaining = time_diff.days
    seconds_in_day = 86400
    total_seconds = time_diff.total_seconds()
    hours_remaining = int(total_seconds / 3600)

    # Determine status
    is_overdue = total_seconds < 0
    if is_overdue:
        days_remaining = -(abs(time_diff.days) + (1 if time_diff.seconds > 0 else 0))

    # Determine priority
    if is_overdue:
        priority_level = "overdue"
    elif days_remaining < 3:
        priority_level = "urgent"
    elif days_remaining < 7:
        priority_level = "warning"
    else:
        priority_level = "normal"

    # Format human-readable string
    if is_overdue:
        abs_days = abs(days_remaining)
        formatted = f"OVERDUE by {abs_days} day{'s' if abs_days != 1 else ''}"
    elif days_remaining == 0:
        formatted = f"{hours_remaining} hour{'s' if hours_remaining != 1 else ''} remaining"
    else:
        formatted = f"{days_remaining} day{'s' if days_remaining != 1 else ''} remaining"

    return {
        "days_remaining": days_remaining,
        "is_overdue": is_overdue,
        "priority_level": priority_level,
        "hours_remaining": hours_remaining,
        "formatted_remaining": formatted,
    }


def get_priority_color(priority_level: str) -> str:
    """
    Map priority level to a color code for UI rendering.

    Args:
        priority_level: One of "urgent", "warning", "normal", "overdue", "unknown".

    Returns:
        Color code: "red" | "yellow" | "green" | "gray".
    """
    color_map = {
        "urgent": "red",
        "warning": "yellow",
        "normal": "green",
        "overdue": "red",
        "unknown": "gray",
    }
    return color_map.get(priority_level, "gray")


def is_deadline_imminent(deadline_date: str, threshold_hours: int = 72) -> bool:
    """
    Quick check: is the deadline within a threshold?

    Args:
        deadline_date: ISO 8601 formatted deadline string.
        threshold_hours: Hours threshold (default: 72 = 3 days).

    Returns:
        True if deadline is within threshold and not overdue.
    """
    info = calculate_deadline_remaining(deadline_date)
    if info["is_overdue"] is None or info["hours_remaining"] is None:
        return False
    if info["is_overdue"]:
        return True  # Overdue is also "imminent" - needs attention
    return 0 <= info["hours_remaining"] <= threshold_hours
