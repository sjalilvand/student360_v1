# app/api/routes_behavior.py
# Behavioral Insights API (Phase 2). Student-scoped via X-Student-Number header.
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import behavioral_service as bs

router = APIRouter()


@router.get("/api/behavior/engagement")
def behavior_engagement(days: int = Query(30, ge=7, le=120),
                        x_student_number: Optional[str] = Header(default=None),
                        db: Session = Depends(get_db)):
    if not x_student_number:
        return {"error": "missing X-Student-Number"}
    return bs.engagement_index(db, x_student_number, days)


@router.get("/api/behavior/insights")
def behavior_insights(days: int = Query(30, ge=7, le=120),
                      x_student_number: Optional[str] = Header(default=None),
                      db: Session = Depends(get_db)):
    if not x_student_number:
        return {"error": "missing X-Student-Number"}
    return bs.insights(db, x_student_number, days)


@router.get("/api/behavior/ranking")
def behavior_ranking(days: int = Query(30, ge=7, le=120),
                     limit: int = Query(50, ge=1, le=200),
                     db: Session = Depends(get_db)):
    return {"days": days, "items": bs.staff_ranking(db, days, limit)}
