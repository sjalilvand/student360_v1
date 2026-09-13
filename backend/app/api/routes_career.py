# app/api/routes_career.py
# Career & skills API (Phase 2 / category 13).
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import skills_service as sks

router = APIRouter()


class EnrichIn(BaseModel):
    limit: int = 6


@router.get("/api/career/skills")
def career_skills(x_student_number: Optional[str] = Header(default=None),
                  db: Session = Depends(get_db)):
    if not x_student_number:
        return {"error": "missing X-Student-Number"}
    return sks.student_skill_profile(db, x_student_number)


@router.get("/api/career/readiness")
def career_readiness(x_student_number: Optional[str] = Header(default=None),
                     db: Session = Depends(get_db)):
    if not x_student_number:
        return {"error": "missing X-Student-Number"}
    return sks.student_skill_profile(db, x_student_number)


@router.get("/api/career/recommend")
def career_recommend(track: str,
                     x_student_number: Optional[str] = Header(default=None),
                     db: Session = Depends(get_db)):
    if not x_student_number:
        return {"error": "missing X-Student-Number"}
    return {"track": track, "items": sks.recommended_courses_for(db, x_student_number, track)}


@router.post("/api/career/enrich")
def career_enrich(body: EnrichIn, db: Session = Depends(get_db)):
    return sks.enrich_courses(db, body.limit)
