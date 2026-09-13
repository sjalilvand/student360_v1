from fastapi import Header, APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.schemas.course_proposal import CourseProposalCreate, CourseProposalResponse
from app.services.proposal_service import ProposalService

router = APIRouter(prefix="/proposals", tags=["Course Proposals"])

@router.post("/", response_model=CourseProposalResponse)
def create_proposal(
    proposal: CourseProposalCreate,
    student_id: int,
    db: Session = Depends(get_db)
):
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
    return {"items": [dict(r) for r in rows]}


@router.get("/{proposal_id}", response_model=CourseProposalResponse)
def get_proposal(proposal_id: int, db: Session = Depends(get_db)):
    service = ProposalService(db)
    return service.get_proposal(proposal_id)
