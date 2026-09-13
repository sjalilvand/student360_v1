# app/api/routes_surveys.py
# Survey 3: term program feedback.
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(prefix="/api/surveys", tags=["Surveys"])


def _student(db: Session, x_student_number: Optional[str]):
    if not x_student_number:
        raise HTTPException(status_code=422, detail="X-Student-Number required")
    sid = db.execute(text(
        "SELECT id FROM stu_students WHERE student_number = :sn"),
        {"sn": str(x_student_number).strip()}).scalar()
    if not sid:
        raise HTTPException(status_code=404, detail="student not found")
    return sid


class TermFeedbackIn(BaseModel):
    term: str = "1405-1"
    rating: int
    comment: Optional[str] = None


@router.get("/term-feedback")
def get_term_feedback(term: str = "1405-1",
                      x_student_number: Optional[str] = Header(default=None),
                      db: Session = Depends(get_db)):
    sid = _student(db, x_student_number)
    row = db.execute(text(
        "SELECT rating, comment, created_at FROM stu_term_feedback "
        "WHERE student_id = :s AND term = :t ORDER BY id DESC LIMIT 1"),
        {"s": sid, "t": term}).mappings().first()
    return {"feedback": dict(row) if row else None}


@router.post("/term-feedback")
def post_term_feedback(body: TermFeedbackIn,
                       x_student_number: Optional[str] = Header(default=None),
                       db: Session = Depends(get_db)):
    sid = _student(db, x_student_number)
    if not (1 <= body.rating <= 5):
        raise HTTPException(status_code=422, detail="امتیاز باید بین ۱ تا ۵ باشد")
    db.execute(text(
        "DELETE FROM stu_term_feedback WHERE student_id = :s AND term = :t"),
        {"s": sid, "t": body.term})
    db.execute(text(
        "INSERT INTO stu_term_feedback (student_id, term, rating, comment) "
        "VALUES (:s, :t, :r, :c)"),
        {"s": sid, "t": body.term, "r": body.rating, "c": body.comment or None})
    db.commit()
    return {"ok": True, "message": "نظر شما درباره برنامه ترم ثبت شد"}
