# app/api/routes_permissions.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import permission_service as ps

router = APIRouter(prefix="/api/permissions", tags=["Access Control"])


class PermIn(BaseModel):
    role: str
    menu_id: str
    enabled: bool


class ResetIn(BaseModel):
    role: str


@router.get("/menu/{role}")
def permissions_menu(role: str, db: Session = Depends(get_db)):
    return ps.menu_for_role(db, role)


@router.get("/matrix")
def permissions_matrix(db: Session = Depends(get_db)):
    return ps.matrix(db)


@router.put("/set")
def permissions_set(body: PermIn, db: Session = Depends(get_db)):
    if not ps.set_enabled(db, body.role, body.menu_id, body.enabled):
        raise HTTPException(status_code=422, detail="نقش نامعتبر است")
    return {"ok": True}


@router.post("/reset")
def permissions_reset(body: ResetIn, db: Session = Depends(get_db)):
    if not ps.reset_role(db, body.role):
        raise HTTPException(status_code=422, detail="نقش نامعتبر است")
    return {"ok": True}
