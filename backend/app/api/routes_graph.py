# app/api/routes_graph.py
# Knowledge graph API (Phase 3 / category 12).
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import knowledge_graph_service as kg

router = APIRouter()


@router.get("/api/graph/stats")
def graph_stats(db: Session = Depends(get_db)):
    return kg.stats(db)


@router.get("/api/graph/roots")
def graph_roots(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    return {"items": kg.roots_for_term(db, limit)}


@router.get("/api/graph/course/{code}")
def graph_course(code: str, db: Session = Depends(get_db)):
    return kg.course_cluster(db, code)


@router.get("/api/graph/path")
def graph_path(frm: str = Query(..., alias="from"),
               to: str = Query(...), db: Session = Depends(get_db)):
    return kg.learning_path(db, frm, to)


@router.post("/api/graph/rebuild")
def graph_rebuild(db: Session = Depends(get_db)):
    kg.invalidate()
    return {"ok": True, **kg.stats(db)}


@router.get("/api/graph/neighbors")
def graph_neighbors(code: str = Query(...), depth: int = Query(2, ge=1, le=4),
                    include_skills: bool = Query(True),
                    db: Session = Depends(get_db)):
    return kg.neighbors_subgraph(db, code, depth, include_skills)
