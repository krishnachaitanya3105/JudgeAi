"""
Deadline scan — inserts notification rows via APScheduler.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.config import get_supabase
from backend.utils.deadline_helper import parse_deadline

logger = logging.getLogger(__name__)

_scheduler: Optional[AsyncIOScheduler] = None


def _within_days(deadline_str: str, max_days: int = 3) -> bool:
    dt = parse_deadline(deadline_str)
    if not dt:
        return False
    now = datetime.now(timezone.utc)
    diff = dt - now
    return timedelta(0) <= diff <= timedelta(days=max_days)


def scan_deadlines_and_notify() -> int:
    """
    Find extracted_actions whose deadline is within the next 3 calendar days
    and enqueue a notifications row.

    Uses server-side date filters to avoid a full table scan as the dataset grows.
    notifications.user_id is NULL unless officers are mapped to alerts separately.
    """
    supabase = get_supabase()
    now = datetime.now(timezone.utc)
    today_iso = now.date().isoformat()
    cutoff_iso = (now + timedelta(days=3)).date().isoformat()

    try:
        # Filter server-side: only rows with deadline in [today, today+3]
        resp = (
            supabase.table("extracted_actions")
            .select("id, case_number, deadline, department")
            .gte("deadline", today_iso)
            .lte("deadline", cutoff_iso)
            .execute()
        )
    except Exception as e:
        logger.warning("Deadline scan skipped (DB error): %s", e)
        return 0

    rows = resp.data or []
    logger.info("Deadline scan: %d upcoming deadline(s) found in [%s, %s]", len(rows), today_iso, cutoff_iso)

    inserted = 0
    seen: set = set()
    for row in rows:
        did = row.get("deadline")
        if not did:
            continue
        dl = did[:10] if isinstance(did, str) else str(did)
        key = f"{row.get('case_number')}:{dl}"
        if key in seen:
            continue
        seen.add(key)
        try:
            msg = (
                f"Compliance deadline approaching ({dl}) for "
                f"{row.get('case_number')} — review within 3 days."
            )
            supabase.table("notifications").insert(
                {
                    "user_id": None,
                    "case_id": str(row.get("id")),
                    "notification_type": "deadline_imminent",
                    "message": msg,
                    "is_read": False,
                    "created_at": now.isoformat(),
                }
            ).execute()
            inserted += 1
        except Exception as err:
            logger.debug("notification insert skipped: %s", err)

    logger.info("Deadline scan queued %s notification(s)", inserted)
    return inserted


def start_scheduler() -> AsyncIOScheduler:
    """Start cron job (daily 08:00 UTC). Safe to call once per process."""
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    sched = AsyncIOScheduler(timezone="UTC")
    sched.add_job(
        scan_deadlines_and_notify,
        CronTrigger(hour=8, minute=0),
        id="deadline_daily_scan",
        replace_existing=True,
    )
    sched.start()
    _scheduler = sched
    logger.info("APScheduler deadline scan started")
    return sched


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler:
        try:
            _scheduler.shutdown(wait=False)
        except Exception:
            pass
        _scheduler = None
