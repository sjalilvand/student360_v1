# app/api/routes_intervention.py
# Smart intervention API (Phase 2): staff loop + student transparency.
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import intervention_service as ivs

router = APIRouter()


class ReviewIn(BaseModel):
    status: str = "reviewed"
    note: Optional[str] = None
    reviewer: Optional[str] = None


@router.post("/api/intervention/run")
def intervention_run(db: Session = Depends(get_db)):
    return ivs.run_scan(db)


@router.get("/api/intervention/list")
def intervention_list(status: Optional[str] = Query(None),
                      db: Session = Depends(get_db)):
    return {"items": ivs.list_interventions(db, status)}


@router.post("/api/intervention/{iid}/review")
def intervention_review(iid: int, body: ReviewIn, db: Session = Depends(get_db)):
    try:
        row = ivs.review(db, iid, body.status, body.note, body.reviewer)
    except ValueError:
        raise HTTPException(status_code=422, detail="وضعیت نامعتبر است")
    except LookupError:
        raise HTTPException(status_code=404, detail="مداخله یافت نشد")
    return {"ok": True, "item": ivs.present(row)}


@router.get("/api/intervention/me")
def intervention_me(x_student_number: Optional[str] = Header(default=None),
                    db: Session = Depends(get_db)):
    if not x_student_number:
        return {"items": []}
    return {"items": ivs.for_student(db, x_student_number)}
