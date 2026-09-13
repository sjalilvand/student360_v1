import json
from fastapi import Header, APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.course_proposal import CourseProposal
from app.schemas.course_proposal import CourseProposalCreate, CourseProposalResponse
from app.services.proposal_service import ProposalService

router = APIRouter(prefix="/proposals", tags=["Course Proposals"])

@router.post("/", response_model=CourseProposalResponse)
def create_proposal(
    proposal: CourseProposalCreate,
    student_id: int,
    db: Session = Depends(get_db)
):

    _dup_ids = set()
    for _p in db.query(CourseProposal).filter(
        CourseProposal.student_id == student_id,
        CourseProposal.term == proposal.term,
    ).all():
        try:
            _dup_ids |= set(json.loads(_p.course_ids or "[]"))
        except Exception:
            pass
    _overlap = sorted(set(proposal.course_ids or []) & _dup_ids)
    if _overlap:
        raise HTTPException(
            status_code=409,
            detail=f"شما برای این درس(ها) در این ترم قبلاً پیشنهاد ثبت کرده‌اید (کد: {_overlap})",
        )
    service = ProposalService(db)
    return service.create_proposal(student_id, proposal)

@router.get("/", response_model=List[CourseProposalResponse])
def get_proposals(
    student_id: Optional[int] = None,
    term: Optional[str] = None,
    db: Session = Depends(get_db)
):
    service = ProposalService(db)
    return service.get_proposals(student_id, term)

@router.get("/all-list")
def proposals_all(db: Session = Depends(get_db)):
    """All proposals with student info (staff view)."""
    rows = db.execute(text(
        "SELECT p.id, p.term, p.course_ids, p.description, p.status, "
        "p.created_at, s.student_number, "
        "TRIM(s.first_name || ' ' || s.last_name) AS full_name "
        "FROM course_proposals p "
        "LEFT JOIN stu_students s ON s.id = p.student_id "
        "ORDER BY p.created_at DESC LIMIT 200")).mappings().all()
    cmap = {r["id"]: f"{r['unique_title']} ({r['unique_code']})"
            for r in db.execute(text(
                "SELECT id, unique_code, unique_title FROM offered_courses")).mappings().all()}
    items = []
    for r in rows:
        d = dict(r)
        try:
            ids = json.loads(d.get("course_ids") or "[]")
        except Exception:
            ids = []
        d["course_titles"] = [cmap.get(int(c), "#" + str(c)) for c in ids
                              if str(c).lstrip("-").isdigit()]
        d["courses_display"] = "، ".join(d["course_titles"]) if d["course_titles"] else "-"
        items.append(d)
    return {"items": items}



@router.get("/mine")
def proposals_mine(x_student_number: str = Header(default=None),
                   db: Session = Depends(get_db)):
    """My proposals with resolved course titles (student view)."""
    if not x_student_number:
        raise HTTPException(status_code=422, detail="X-Student-Number required")
    stu = db.execute(text(
        "SELECT id FROM stu_students WHERE student_number = :sn"),
        {"sn": str(x_student_number).strip()}).first()
    if not stu:
        return {"items": []}
    rows = db.execute(text(
        "SELECT id, term, course_ids, description, status, created_at "
        "FROM course_proposals WHERE student_id = :sid "
        "ORDER BY created_at DESC LIMIT 50"), {"sid": stu[0]}).mappings().all()
    cmap = {r["id"]: f"{r['unique_title']} ({r['unique_code']})"
            for r in db.execute(text(
                "SELECT id, unique_code, unique_title FROM offered_courses")).mappings().all()}
    items = []
    for r in rows:
        d = dict(r)
        try:
            ids = json.loads(d.get("course_ids") or "[]")
        except Exception:
            ids = []
        d["course_titles"] = [cmap.get(int(c), "#" + str(c)) for c in ids
                              if str(c).lstrip("-").isdigit()]
        d["courses_display"] = "، ".join(d["course_titles"]) if d["course_titles"] else "-"
        items.append(d)
    return {"items": items}


@router.get("/course-options")
def proposals_course_options(db: Session = Depends(get_db)):
    """Single source of truth for pickers: offered_courses (id/code/title)."""
    rows = db.execute(text(
        "SELECT id, unique_code AS code, unique_title AS title "
        "FROM offered_courses WHERE is_active = 1 "
        "ORDER BY unique_title")).mappings().all()
    return {"items": [dict(r) for r in rows]}

@router.get("/{proposal_id}", response_model=CourseProposalResponse)
def get_proposal(proposal_id: int, db: Session = Depends(get_db)):
    service = ProposalService(db)
    return service.get_proposal(proposal_id)
