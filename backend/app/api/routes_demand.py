# app/api/routes_demand.py
# Demand prediction runner (Phase 1): wires demand_service into HTTP and
# persists results into offered_courses.demand_prediction (the service itself
# only computes - persistence is the caller's job).
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import demand_service as ds
from app.services import event_tracking_service as ets

router = APIRouter()


class DemandRunIn(BaseModel):
    semester: str = "mehr"
    limit: Optional[int] = None  # optional cap (testing)


@router.post("/api/demand/run")
def demand_run(body: DemandRunIn, db: Session = Depends(get_db)):
    ids = [r[0] for r in db.execute(text("SELECT id FROM offered_courses")).all()]
    if body.limit:
        ids = ids[: max(1, min(int(body.limit), len(ids)))]
    if not ids:
        return {"ok": False, "detail": "no offered courses in DB"}

    preds = ds.predict_demand_batch(ids, body.semester)  # {course_id: int}

    updated = 0
    for cid, val in preds.items():
        db.execute(
            text("UPDATE offered_courses SET demand_prediction = :v WHERE id = :cid"),
            {"v": float(val), "cid": int(cid)},
        )
        updated += 1
    db.commit()

    try:
        ets.track_event(db, event_type="demand_predicted", event_name=body.semester,
                        source="system", payload={"courses": updated})
    except Exception:
        pass

    top = db.execute(text(
        "SELECT id, unique_code, unique_title, demand_prediction "
        "FROM offered_courses WHERE demand_prediction IS NOT NULL "
        "ORDER BY demand_prediction DESC LIMIT 5")).mappings().all()
    return {"ok": True, "semester": body.semester, "updated": updated,
            "top": [dict(r) for r in top]}
