# app/api/routes_staff.py
# Staff workspace (education-expert) - pilot: read-only overview + students.
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.event_log import StuEventLog

router = APIRouter()


@router.get("/api/staff/overview")
def staff_overview(db: Session = Depends(get_db)):
    out = {"students": None, "programs": None, "alerts": None,
           "discrepancies_pending": None, "events_24h": None}
    try:
        out["students"] = db.execute(text("SELECT COUNT(*) FROM stu_students")).scalar()
        out["programs"] = db.execute(text("SELECT COUNT(*) FROM stu_programs")).scalar()
    except Exception:
        pass
    try:
        out["alerts"] = db.execute(text("SELECT COUNT(*) FROM stu_alerts")).scalar()
    except Exception:
        pass
    try:
        out["discrepancies_pending"] = db.execute(
            text("SELECT COUNT(*) FROM stu_discrepancy_reports WHERE status = 'open'")).scalar()
    except Exception:
        try:
            out["discrepancies_pending"] = db.execute(
                text("SELECT COUNT(*) FROM stu_discrepancy_reports")).scalar()
        except Exception:
            pass
    try:
        since = datetime.utcnow() - timedelta(hours=24)
        out["events_24h"] = db.query(StuEventLog).filter(
            StuEventLog.occurred_at >= since).count()
    except Exception:
        pass

    recent_logins = []
    try:
        rows = (db.query(StuEventLog)
                .filter(StuEventLog.event_type == "login")
                .order_by(StuEventLog.occurred_at.desc())
                .limit(8).all())
        recent_logins = [{"who": r.student_ref, "via": r.event_name,
                          "at": r.occurred_at.isoformat() if r.occurred_at else None,
                          "src": r.source} for r in rows]
    except Exception:
        pass
    out["recent_logins"] = recent_logins
    return out


@router.get("/api/staff/students")
def staff_students(db: Session = Depends(get_db)):
    rows = []
    try:
        res = db.execute(text(
            "SELECT s.id, s.student_number, TRIM(s.first_name || ' ' || s.last_name) AS full_name, "
            "s.status AS student_status, p.title AS program, "
            "g.weighted_gpa, g.total_credits, g.graded_courses "
            "FROM stu_students s "
            "LEFT JOIN stu_programs p ON p.id = s.program_id "
            "LEFT JOIN v_student_gpa g ON g.student_id = s.id "
            "ORDER BY s.student_number")).mappings().all()
        rows = [dict(r) for r in res]
    except Exception:
        pass
    return {"count": len(rows), "items": rows}
