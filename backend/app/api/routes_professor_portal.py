# app/api/routes_professor_portal.py
# Professor portal (Phase B1): login, me, profile, change-password, stats.
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.prof_auth_utils import (
    check_password_hash,
    create_token,
    current_professor_id,
    generate_password_hash,
)

router = APIRouter(prefix="/api/professor", tags=["Professor Portal"])


def _user_by_username(db: Session, username: str):
    return db.execute(text(
        "SELECT id, username, display_name, role, ref_id, password_hash "
        "FROM stu_unified_users WHERE username = :u AND role = 'professor'"),
        {"u": username}).mappings().first()


def _user_by_request(request: Request, db: Session):
    prof_id = current_professor_id(request)
    if not prof_id:
        return None
    return db.execute(text(
        "SELECT id, username, display_name, role, ref_id, password_hash "
        "FROM stu_unified_users WHERE id = :i"),
        {"i": prof_id}).mappings().first()


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/login")
def professor_login(body: LoginIn, db: Session = Depends(get_db)):
    username = (body.username or "").strip()
    password = body.password or ""
    if not username or not password:
        raise HTTPException(status_code=400, detail="نام کاربری و رمز عبور الزامی است")

    user = _user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=401, detail="نام کاربری یا رمز عبور اشتباه است")

    stored = user["password_hash"]
    if not stored:
        # first login sets the password (legacy Flask behavior)
        db.execute(text("UPDATE stu_unified_users SET password_hash = :h WHERE id = :i"),
                   {"h": generate_password_hash(password), "i": user["id"]})
        db.commit()
    elif not check_password_hash(stored, password):
        raise HTTPException(status_code=401, detail="نام کاربری یا رمز عبور اشتباه است")

    token = create_token(user["id"])
    return {"token": token, "role": "professor",
            "user": {"id": user["id"], "full_name": user["display_name"],
                     "username": user["username"], "photo": None}}


@router.get("/me")
def professor_me(request: Request, db: Session = Depends(get_db)):
    user = _user_by_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="نشست نامعتبر است")
    prof_id = user["ref_id"]
    stats = {"proposals_total": 0, "proposals_pending": 0,
             "availability_slots": 0, "max_units": None}
    if prof_id:
        stats["proposals_total"] = db.execute(text(
            "SELECT COUNT(*) FROM teaching_preferences "
            "WHERE instructor_code = :c"), {"c": str(prof_id)}).scalar() or 0
        stats["proposals_pending"] = db.execute(text(
            "SELECT COUNT(*) FROM teaching_preferences "
            "WHERE instructor_code = :c AND status = 'pending'"),
            {"c": str(prof_id)}).scalar() or 0
        stats["availability_slots"] = db.execute(text(
            "SELECT COUNT(*) FROM time_preferences "
            "WHERE instructor_code = :c"), {"c": str(prof_id)}).scalar() or 0
        stats["max_units"] = db.execute(text(
            "SELECT max_teaching_units FROM instructors WHERE code = :c"),
            {"c": str(prof_id)}).scalar()
    return {"user": {"id": user["id"], "username": user["username"],
                     "full_name": user["display_name"], "prof_id": prof_id},
            "stats": stats}


class PasswordIn(BaseModel):
    old_password: str = ""
    new_password: str


@router.post("/change-password")
def professor_change_password(body: PasswordIn, request: Request,
                              db: Session = Depends(get_db)):
    user = _user_by_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="نشست نامعتبر است")
    stored = user["password_hash"]
    if stored and not check_password_hash(stored, body.old_password):
        raise HTTPException(status_code=401, detail="رمز عبور فعلی اشتباه است")
    if len(body.new_password) < 4:
        raise HTTPException(status_code=422, detail="رمز جدید حداقل ۴ کاراکتر")
    db.execute(text("UPDATE stu_unified_users SET password_hash = :h WHERE id = :i"),
               {"h": generate_password_hash(body.new_password), "i": user["id"]})
    db.commit()
    return {"ok": True, "message": "رمز عبور تغییر کرد"}
