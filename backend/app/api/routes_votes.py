from fastapi import Header, APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.course_vote import CourseVote
from app.schemas.course_vote import CourseVoteCreate, CourseVoteResponse
from app.services.vote_service import VoteService

router = APIRouter(prefix="/votes", tags=["Course Votes"])

@router.post("/", response_model=CourseVoteResponse)
def create_vote(
    vote: CourseVoteCreate,
    student_id: int,
    db: Session = Depends(get_db)
):

    _dup = db.query(CourseVote).filter(
        CourseVote.student_id == student_id,
        CourseVote.course_id == vote.course_id,
        CourseVote.term == vote.term,
        CourseVote.vote_type == vote.vote_type,
    ).first()
    if _dup:
        raise HTTPException(
            status_code=409,
            detail="شما قبلاً همین رأی را برای این درس در این ترم ثبت کرده‌اید",
        )
    """دانشجو به یک درس رأی می‌دهد (لایک یا درخواست ارائه)"""
    service = VoteService(db)
    return service.create_vote(student_id, vote)

@router.get("/", response_model=List[CourseVoteResponse])
def get_votes(
    student_id: Optional[int] = None,
    course_id: Optional[int] = None,
    term: Optional[str] = None,
    db: Session = Depends(get_db)
):
    service = VoteService(db)
    return service.get_votes(student_id, course_id, term)

@router.get("/stats/{course_id}")
def get_vote_stats(course_id: int, term: str, db: Session = Depends(get_db)):
    """آمار رأی‌های یک درس در یک ترم مشخص"""
    service = VoteService(db)
    return service.get_vote_stats(course_id, term)

@router.get("/me-id")
def votes_me_id(x_student_number: str = Header(default=None),
                db: Session = Depends(get_db)):
    """Resolve the DB id of the requesting student (X-Student-Number)."""
    if not x_student_number:
        raise HTTPException(status_code=422, detail="X-Student-Number required")
    row = db.execute(
        text("SELECT id FROM stu_students WHERE student_number = :sn"),
        {"sn": str(x_student_number).strip()},
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="student not found")
    return {"student_id": row[0]}


@router.get("/stats-all")
def votes_stats_all(db: Session = Depends(get_db)):
    """Aggregate vote counts per course (for students & staff)."""
    rows = db.execute(text(
        "SELECT cv.course_id AS course_id, "
        "COALESCE(oc.unique_title, '') AS title, "
        "COALESCE(oc.unique_code, '') AS code, "
        "SUM(CASE WHEN cv.vote_type = 'like' THEN 1 ELSE 0 END) AS likes, "
        "SUM(CASE WHEN cv.vote_type = 'request' THEN 1 ELSE 0 END) AS requests, "
        "COUNT(*) AS total "
        "FROM course_votes cv "
        "LEFT JOIN offered_courses oc ON oc.id = cv.course_id "
        "GROUP BY cv.course_id, oc.unique_title, oc.unique_code "
        "ORDER BY total DESC")).mappings().all()
    return {"items": [dict(r) for r in rows]}
