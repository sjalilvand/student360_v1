# app/api/routes_twin.py
# Digital Twin what-if simulation API (Phase 3 kickoff).
from typing import Optional

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import digital_twin_service as twin

router = APIRouter()


class TwinCourse(BaseModel):
    code: Optional[str] = None
    title: Optional[str] = None
    credits: int
    expected_grade: float


class TwinIn(BaseModel):
    courses: Optional[list[TwinCourse]] = None
    units: Optional[int] = None
    avg_grade: Optional[float] = None


@router.post("/api/twin/simulate")
def twin_simulate(body: TwinIn,
                  x_student_number: Optional[str] = Header(default=None),
                  db: Session = Depends(get_db)):
    if not x_student_number:
        return {"error": "missing X-Student-Number"}
    courses = [c.model_dump() for c in (body.courses or [])]
    return twin.simulate(db, x_student_number, courses,
                         body.units, body.avg_grade)
