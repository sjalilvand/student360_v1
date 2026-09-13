# app/api/routes_ratings.py  (v2 - course rating survey, student-scoped)
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(prefix="/api/ratings", tags=["Course Ratings"])


def _student(db: Session, x_student_number: Optional[str]):
    if not x_student_number:
        raise HTTPException(status_code=422, detail="X-Student-Number required")
    sid = db.execute(text(
        "SELECT id FROM stu_students WHERE student_number = :sn"),
        {"sn": str(x_student_number).strip()}).scalar()
    if not sid:
        raise HTTPException(status_code=404, detail="student not found")
    return sid


@router.get("/my-courses")
def my_rating_courses(x_student_number: Optional[str] = Header(default=None),
                      term: str = "1405-1", db: Session = Depends(get_db)):
    """Active rating-poll courses + my existing rating for each."""
    sid = _student(db, x_student_number)
    rows = db.execute(text(
        "SELECT vp.course_id AS course_id, "
        "COALESCE(oc.unique_title, '') AS title, "
        "COALESCE(oc.unique_code, '') AS code, "
        "cr.rating AS my_rating, cr.comment AS my_comment "
        "FROM vote_polls vp "
        "LEFT JOIN offered_courses oc ON oc.id = vp.course_id "
        "LEFT JOIN course_ratings cr ON cr.course_id = vp.course_id "
        "  AND cr.student_id = :sid "
        "WHERE vp.is_active = 1 AND vp.survey_type = 'rating' AND vp.term = :t "
        "ORDER BY oc.unique_title"), {"sid": sid, "t": term}).mappings().all()
    return {"items": [dict(r) for r in rows]}


class RateIn(BaseModel):
    course_id: int
    rating: int
    comment: Optional[str] = None
    term: str = "1405-1"


@router.post("/rate")
def rate_course(body: RateIn, x_student_number: Optional[str] = Header(default=None),
                db: Session = Depends(get_db)):
    sid = _student(db, x_student_number)
    if not (1 <= body.rating <= 5):
        raise HTTPException(status_code=422, detail="امتیاز باید بین ۱ تا ۵ باشد")
    active = db.execute(text(
        "SELECT id FROM vote_polls WHERE course_id = :c AND survey_type='rating' "
        "AND is_active = 1 AND term = :t"), {"c": body.course_id, "t": body.term}).first()
    if not active:
        raise HTTPException(status_code=422, detail="این درس در نظرسنجی فعال نیست")
    db.execute(text("DELETE FROM course_ratings WHERE student_id = :s AND course_id = :c"),
               {"s": sid, "c": body.course_id})
    db.execute(text(
        "INSERT INTO course_ratings (student_id, course_id, rating, comment, term) "
        "VALUES (:s, :c, :r, :cm, :t)"),
        {"s": sid, "c": body.course_id, "r": body.rating,
         "cm": body.comment or None, "t": body.term})
    db.commit()
    return {"ok": True, "message": "امتیاز شما ثبت شد"}


@router.get("/stats-all")
def ratings_stats_all(db: Session = Depends(get_db)):
    rows = db.execute(text(
        "SELECT cr.course_id AS course_id, "
        "COALESCE(oc.unique_title, '') AS title, COALESCE(oc.unique_code, '') AS code, "
        "ROUND(AVG(cr.rating), 2) AS avg_rating, COUNT(*) AS votes "
        "FROM course_ratings cr "
        "LEFT JOIN offered_courses oc ON oc.id = cr.course_id "
        "WHERE cr.course_id IS NOT NULL "
        "GROUP BY cr.course_id, oc.unique_title, oc.unique_code "
        "ORDER BY votes DESC")).mappings().all()
    return {"items": [dict(r) for r in rows]}

