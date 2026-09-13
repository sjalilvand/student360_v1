# app/api/routes_profile_mart.py
# Bridge: Data Mart (v_student_gpa) -> Smart Profile.
from typing import Optional

from fastapi import APIRouter, Depends, Header
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter()


@router.get("/api/student360/profile/gpa-mart")
def gpa_mart(x_student_number: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    """Weighted GPA from the Data Mart for the requesting student (X-Student-Number header)."""
    if not x_student_number:
        return {"found": False, "reason": "missing X-Student-Number header"}
    rows = db.execute(
        text(
            "SELECT student_number, full_name, graded_courses, total_credits, avg_score, weighted_gpa "
            "FROM v_student_gpa WHERE student_number = :sn"
        ),
        {"sn": str(x_student_number).strip()},
    ).mappings().all()
    if not rows:
        return {"found": False, "student_number": str(x_student_number)}
    r = dict(rows[0])
    r.update({"found": True, "source": "v_student_gpa (Data Mart)"})
    return r
