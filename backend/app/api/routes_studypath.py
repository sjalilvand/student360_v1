# app/api/routes_studypath.py
# Personalized study path API (Phase 2): student self-view + staff by-number.
from typing import Optional

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import study_path_service as sps

router = APIRouter()


@router.get("/api/studypath/me")
def studypath_me(x_student_number: Optional[str] = Header(default=None),
                 db: Session = Depends(get_db)):
    if not x_student_number:
        return {"error": "missing X-Student-Number"}
    return sps.build_path(db, x_student_number)


@router.get("/api/studypath/{student_number}")
def studypath_for(student_number: str, db: Session = Depends(get_db)):
    return sps.build_path(db, student_number)
