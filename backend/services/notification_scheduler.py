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
    Find extracted_actions whose deadline is within 3 calendar days ahead
    (not overdue) and enqueue a notifications row.

    notifications.user_id is NULL unless you map officers to alerts separately.
    """
    supabase = get_supabase()
    try:
        resp = (
            supabase.table("extracted_actions")
            .select("id, case_number, deadline, department")
            .execute()
        )
    except Exception as e:
        logger.warning("Deadline scan skipped (DB error): %s", e)
        return 0

    rows = resp.data or []
    inserted = 0
    seen = set()
    for row in rows:
        did = row.get("deadline")
        if not did:
            continue
        dl = did[:10] if isinstance(did, str) else str(did)
        if not _within_days(dl):
            continue
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
                    "created_at": datetime.now(timezone.utc).isoformat(),
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
