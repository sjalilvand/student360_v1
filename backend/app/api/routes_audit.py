# app/api/routes_audit.py
# Audit endpoints (login history from event log).
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.event_log import StuEventLog

router = APIRouter()


@router.get("/api/v1/audit/logins")
def audit_logins(limit: int = Query(40, ge=1, le=200), db: Session = Depends(get_db)):
    rows = (
        db.query(StuEventLog)
        .filter(StuEventLog.event_type.in_(["login", "logout"]))
        .order_by(StuEventLog.occurred_at.desc())
        .limit(limit)
        .all()
    )
    return {"count": len(rows), "items": [r.to_dict() for r in rows]}
