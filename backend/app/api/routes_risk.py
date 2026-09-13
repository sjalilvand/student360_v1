# app/api/routes_risk.py
# Academic risk API (Phase 2 / category 14). Student self-view + staff list.
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import risk_service as rs

router = APIRouter()


@router.get("/api/risk/me")
def risk_me(x_student_number: Optional[str] = Header(default=None),
            db: Session = Depends(get_db)):
    if not x_student_number:
        return {"error": "missing X-Student-Number"}
    return rs.compute_risk(db, x_student_number)


@router.get("/api/risk/list")
def risk_list(limit: int = Query(50, ge=1, le=200),
              db: Session = Depends(get_db)):
    return {"items": rs.list_risks(db, limit)}
