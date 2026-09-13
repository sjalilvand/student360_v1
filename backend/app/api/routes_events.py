# app/api/routes_events.py
# Event Tracking API (STU-EVT)
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import event_tracking_service as ets

router = APIRouter()


class EventIn(BaseModel):
    event_type: str = Field(..., min_length=2, max_length=50)
    event_name: Optional[str] = None
    student_ref: Optional[str] = None
    session_ref: Optional[str] = None
    source: str = "web"
    payload: Optional[dict] = None


@router.post("/api/events")
def track_event(body: EventIn, db: Session = Depends(get_db)):
    """Record one event (called by frontend and other services)."""
    try:
        evt = ets.track_event(
            db,
            event_type=body.event_type,
            event_name=body.event_name,
            student_ref=body.student_ref,
            session_ref=body.session_ref,
            source=body.source,
            payload=body.payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"ok": True, "event": evt.to_dict()}


@router.get("/api/events/summary")
def events_summary(days: int = Query(30, ge=1, le=365), student_ref: Optional[str] = None,
                   db: Session = Depends(get_db)):
    """Aggregated event dashboard (foundation of Phase-2 Behavioral Insights)."""
    return ets.summarize(db, days=days, student_ref=student_ref)


@router.get("/api/events/recent")
def events_recent(limit: int = Query(50, ge=1, le=500), student_ref: Optional[str] = None,
                  db: Session = Depends(get_db)):
    """Raw recent events (admin/testing)."""
    return [e.to_dict() for e in ets.list_recent(db, limit=limit, student_ref=student_ref)]
