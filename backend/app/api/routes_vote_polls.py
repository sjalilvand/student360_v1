# app/api/routes_vote_polls.py  (v2 - survey types: request | rating)
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(prefix="/api/vote-polls", tags=["Vote Polls"])
SURVEY_TYPES = ("request", "rating")


def _student_id(db: Session, x_student_number: Optional[str]):
    if not x_student_number:
        return None
    return db.execute(text(
        "SELECT id FROM stu_students WHERE student_number = :sn"),
        {"sn": str(x_student_number).strip()}).scalar()


class PollUpdate(BaseModel):
    course_id: int
    survey_type: str = "request"
    term: str = "1405-1"
    is_active: bool


@router.get("/active")
def active_polls(survey_type: str = "request", term: str = "1405-1",
                 x_student_number: Optional[str] = Header(default=None),
                 db: Session = Depends(get_db)):
    if survey_type not in SURVEY_TYPES:
        raise HTTPException(status_code=422, detail="نوع نظرسنجی نامعتبر")
    sid = _student_id(db, x_student_number)
    rows = db.execute(text(
        "SELECT vp.course_id AS course_id, "
        "COALESCE(oc.unique_title, '') AS title, "
        "COALESCE(oc.unique_code, '') AS code, "
        "COALESCE(oc.capacity, 0) AS capacity, "
        "SUM(CASE WHEN cv.vote_type = 'request' THEN 1 ELSE 0 END) AS requests, "
        "CASE WHEN :sid IS NOT NULL AND EXISTS ("
        "  SELECT 1 FROM course_votes cv2 "
        "  WHERE cv2.course_id = vp.course_id AND cv2.term = vp.term "
        "  AND cv2.student_id = :sid AND cv2.vote_type = 'request' "
        ") THEN 1 ELSE 0 END AS my_request "
        "FROM vote_polls vp "
        "LEFT JOIN offered_courses oc ON oc.id = vp.course_id "
        "LEFT JOIN course_votes cv ON cv.course_id = vp.course_id AND cv.term = vp.term "
        "WHERE vp.is_active = 1 AND vp.survey_type = :st AND vp.term = :t "
        "GROUP BY vp.course_id, oc.unique_title, oc.unique_code, oc.capacity, vp.term "
        "ORDER BY requests DESC"), {"st": survey_type, "t": term, "sid": sid}).mappings().all()
    return {"items": [dict(r) for r in rows]}


@router.put("/update")
def poll_update(body: PollUpdate, db: Session = Depends(get_db)):
    """Admin: activate/deactivate a course in a survey."""
    if body.survey_type not in SURVEY_TYPES:
        raise HTTPException(status_code=422, detail="نوع نظرسنجی نامعتبر")
    if body.is_active:
        exists = db.execute(text(
            "SELECT id FROM vote_polls WHERE course_id = :c AND survey_type = :st "
            "AND term = :t"), {"c": body.course_id, "st": body.survey_type,
                              "t": body.term}).first()
        if not exists:
            db.execute(text(
                "INSERT INTO vote_polls (course_id, term, survey_type, is_active) "
                "VALUES (:c, :t, :st, 1)"),
                {"c": body.course_id, "t": body.term, "st": body.survey_type})
            db.commit()
        return {"ok": True, "active": True}
    db.execute(text(
        "DELETE FROM vote_polls WHERE course_id = :c AND survey_type = :st AND term = :t"),
        {"c": body.course_id, "st": body.survey_type, "t": body.term})
    db.commit()
    return {"ok": True, "active": False}
