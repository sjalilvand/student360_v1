# app/api/routes_marts.py
# Data Mart API (Phase 1 / Data Fast Track).
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import engine, get_db
from app.services import data_mart_service as dms

router = APIRouter()


@router.get("/api/marts/status")
def marts_status():
    return dms.status(engine)


@router.post("/api/marts/refresh")
def marts_refresh():
    return dms.refresh_marts(engine)


@router.get("/api/marts/{view_name}/sample")
def marts_sample(view_name: str, limit: int = Query(20, ge=1, le=100)):
    try:
        return {"view": view_name, "rows": dms.sample(engine, view_name, limit)}
    except ValueError:
        raise HTTPException(status_code=404, detail="unknown view")
