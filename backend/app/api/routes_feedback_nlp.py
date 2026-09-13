# app/api/routes_feedback_nlp.py
# Feedback quality API (staff-facing).
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import feedback_nlp_service as fn

router = APIRouter()


class AnalyzeIn(BaseModel):
    days: int = 30


@router.get("/api/feedback/quality")
def feedback_quality(days: int = Query(30, ge=7, le=180),
                     db: Session = Depends(get_db)):
    return {**fn.collect(db, days), "latest_insight": fn.latest(db)}


@router.post("/api/feedback/analyze")
def feedback_analyze(body: AnalyzeIn, db: Session = Depends(get_db)):
    return fn.llm_analyze(db, body.days)
