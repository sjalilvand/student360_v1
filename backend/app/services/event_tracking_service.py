# app/services/event_tracking_service.py
# Event Tracking service (STU-EVT): write + aggregate events.
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.event_log import StuEventLog

KNOWN_EVENT_TYPES = {
    "login", "logout", "page_view", "regulation_ask", "guide_open",
    "scenario_created", "scenario_viewed", "course_analyzed",
    "graduation_check", "calendar_viewed", "alert_viewed",
    "quiz_started", "quiz_submitted", "professor_asked",
    "discrepancy_reported", "counseling_requested",
}


def track_event(db: Session, event_type: str, event_name=None, student_ref=None,
                session_ref=None, source="api", payload=None) -> StuEventLog:
    """Insert one event row. Unknown types are accepted (open schema)."""
    if not event_type or not str(event_type).strip():
        raise ValueError("invalid event_type")
    evt = StuEventLog(
        student_ref=(str(student_ref)[:50] if student_ref else None),
        event_type=str(event_type).strip().lower()[:50],
        event_name=(str(event_name)[:100] if event_name else None),
        source=(str(source)[:20] if source else "api"),
        session_ref=(str(session_ref)[:64] if session_ref else None),
        payload=(json.dumps(payload, ensure_ascii=False) if payload else None),
        occurred_at=datetime.utcnow(),
    )
    db.add(evt)
    db.commit()
    db.refresh(evt)
    return evt


def list_recent(db: Session, limit: int = 50, student_ref=None):
    q = db.query(StuEventLog)
    if student_ref:
        q = q.filter(StuEventLog.student_ref == str(student_ref))
    return q.order_by(StuEventLog.occurred_at.desc()).limit(max(1, min(int(limit), 500))).all()


def summarize(db: Session, days: int = 30, student_ref=None):
    since = datetime.utcnow() - timedelta(days=max(1, min(int(days), 365)))
    q = db.query(StuEventLog).filter(StuEventLog.occurred_at >= since)
    if student_ref:
        q = q.filter(StuEventLog.student_ref == str(student_ref))
    rows = q.all()
    by_type = Counter(r.event_type for r in rows)
    by_day = Counter(r.occurred_at.strftime("%Y-%m-%d") for r in rows)
    by_source = Counter((r.source or "api") for r in rows)
    students = len({r.student_ref for r in rows if r.student_ref})
    return {
        "days": int(days),
        "student_ref": student_ref,
        "total": len(rows),
        "distinct_students": students,
        "by_type": dict(by_type.most_common()),
        "by_source": dict(by_source),
        "by_day": dict(sorted(by_day.items())),
        "last_event_at": (max(r.occurred_at for r in rows).isoformat() if rows else None),
    }
