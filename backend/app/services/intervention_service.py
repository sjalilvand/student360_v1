# app/services/intervention_service.py  (v2 - cooldown-aware)
# Smart Intervention: bridge risk warnings -> staff action loop (Phase 2).
# Idempotency: open/in_progress dedupes; reviewed/closed within COOLDOWN_DAYS
# is not re-created (prevents review->rescan->duplicate infinite loop).
from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.intervention import STATUS_LABELS, StuIntervention
from app.services import event_tracking_service as ets
from app.services import risk_service as rs

ALLOWED_STATUSES = ("open", "in_progress", "reviewed", "closed")
COOLDOWN_DAYS = 7


def present(row: StuIntervention) -> dict:
    d = row.to_dict()
    for k in ("reasons", "suggested_actions"):
        try:
            d[k] = json.loads(d[k]) if d[k] else []
        except Exception:
            d[k] = []
    return d


def run_scan(db: Session) -> dict:
    """Create interventions for risky students (idempotent + cooldown).
    Rule: create when risk_level != 'پایین' OR risk_score >= 25.
    Skip when: (a) open/in_progress exists, or (b) ANY intervention created
    within the last COOLDOWN_DAYS (regardless of status)."""
    risks = rs.list_risks(db, limit=200)
    cutoff = datetime.utcnow() - timedelta(days=COOLDOWN_DAYS)
    created, skipped = [], []
    for r in risks:
        if r["risk_level"] == "پایین" and r["risk_score"] < 25:
            continue
        sn = r["student_number"]

        open_exists = (db.query(StuIntervention)
                       .filter(StuIntervention.student_number == sn,
                               StuIntervention.status.in_(["open", "in_progress"]))
                       .first())
        if open_exists:
            skipped.append(sn)
            continue

        recent = (db.query(StuIntervention)
                  .filter(StuIntervention.student_number == sn,
                          StuIntervention.created_at >= cutoff)
                  .first())
        if recent:
            skipped.append(sn)
            continue

        row = StuIntervention(
            student_number=sn,
            student_name=r.get("student_name"),
            risk_score=r["risk_score"],
            risk_level=r["risk_level"],
            reasons=json.dumps(r["reasons"], ensure_ascii=False),
            suggested_actions=json.dumps(r["suggested_actions"], ensure_ascii=False),
            status="open",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        created.append(sn)
        try:
            ets.track_event(db, event_type="intervention_created",
                            event_name=r["risk_level"],
                            student_ref=sn, source="system",
                            payload={"score": r["risk_score"], "id": row.id})
        except Exception:
            pass
    return {"scanned": len(risks), "created": created, "skipped": skipped,
            "cooldown_days": COOLDOWN_DAYS}


def list_interventions(db: Session, status=None) -> list:
    q = db.query(StuIntervention)
    if status and status in ALLOWED_STATUSES:
        q = q.filter(StuIntervention.status == status)
    rows = q.order_by(StuIntervention.created_at.desc()).limit(200).all()
    return [present(x) for x in rows]


def review(db: Session, intervention_id: int, status: str,
           note=None, reviewer=None) -> StuIntervention:
    if status not in ALLOWED_STATUSES:
        raise ValueError("invalid status")
    row = db.query(StuIntervention).filter(
        StuIntervention.id == int(intervention_id)).first()
    if not row:
        raise LookupError("not found")
    row.status = status
    row.review_note = (note or "").strip() or None
    row.reviewed_by = reviewer or "staff"
    row.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    try:
        ets.track_event(db, event_type="intervention_reviewed", event_name=status,
                        student_ref=row.student_number, source="api",
                        payload={"id": row.id, "by": row.reviewed_by})
    except Exception:
        pass
    return row


def for_student(db: Session, student_number: str) -> list:
    rows = (db.query(StuIntervention)
            .filter(StuIntervention.student_number == str(student_number))
            .order_by(StuIntervention.created_at.desc()).limit(20).all())
    out = []
    for x in rows:
        d = present(x)
        d.pop("reasons", None)           # internal detail: staff-only
        d.pop("suggested_actions", None)
        out.append(d)
    return out


def cleanup_duplicates(db: Session) -> dict:
    """One-time housekeeping: keep the OLDEST intervention per student,
    delete newer duplicates (created by the pre-cooldown bug)."""
    removed = 0
    rows = (db.query(StuIntervention)
            .order_by(StuIntervention.student_number, StuIntervention.created_at)
            .all())
    seen = set()
    for row in rows:
        if row.student_number in seen:
            db.delete(row)
            removed += 1
        else:
            seen.add(row.student_number)
    db.commit()
    return {"removed": removed}
