# app/api/routes_adaptive_quiz.py
# Adaptive quiz API (Phase 2): generate / submit / history.
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import adaptive_quiz_service as aqs

router = APIRouter()


class NextIn(BaseModel):
    course_code: str


class SubmitIn(BaseModel):
    answers: list


@router.post("/api/adaptive-quiz/next")
def aq_next(body: NextIn, x_student_number: Optional[str] = Header(default=None),
            db: Session = Depends(get_db)):
    if not x_student_number:
        return {"error": "missing X-Student-Number"}
    return aqs.generate(db, x_student_number, body.course_code)


@router.post("/api/adaptive-quiz/{quiz_id}/submit")
def aq_submit(quiz_id: int, body: SubmitIn,
              x_student_number: Optional[str] = Header(default=None),
              db: Session = Depends(get_db)):
    if not x_student_number:
        return {"error": "missing X-Student-Number"}
    try:
        return aqs.submit(db, x_student_number, quiz_id, body.answers)
    except LookupError:
        raise HTTPException(status_code=404, detail="کوییز یافت نشد")


@router.get("/api/adaptive-quiz/history")
def aq_history(x_student_number: Optional[str] = Header(default=None),
               db: Session = Depends(get_db)):
    if not x_student_number:
        return {"items": []}
    return {"items": aqs.history(db, x_student_number)}
