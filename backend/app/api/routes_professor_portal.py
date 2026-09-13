# app/api/routes_professor_portal.py  (v2 - full professor portal)
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.prof_auth_utils import (
    check_password_hash,
    create_token,
    generate_password_hash,
    parse_token,
)

router = APIRouter(prefix="/api/professor", tags=["Professor Portal"])

_INVISIBLE = ("\u200b", "\u200c", "\u200e", "\u200f", "\ufeff")


def _clean(s):
    s = (s or "").lower()
    s = s.replace("\u064a", "\u06cc").replace("\u0643", "\u06a9")
    for ch in _INVISIBLE:
        s = s.replace(ch, "")
    return " ".join(s.split())


def _user_by_request(request: Request, db: Session):
    auth = (request.headers.get("authorization") or "")
    if not auth.lower().startswith("bearer "):
        return None
    import time as _t
    try:
        import base64, hmac, hashlib
        body, sig = auth.split(" ", 1)[1].strip().split(".", 1)
        pad = "=" * (-len(sig) % 4)
        import base64 as b64mod
        raw_sig = b64mod.urlsafe_b64decode(sig + pad)
        secret = (__import__("os").getenv("PROF_JWT_SECRET") or "student360-prof-secret-fallback").encode()
        expected = hmac.new(secret, body.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(raw_sig, expected):
            return None
        payload = json.loads(b64mod.urlsafe_b64decode(body + pad))
        if payload.get("exp", 0) < _t.time():
            return None
        return db.execute(text(
            "SELECT id, username, display_name, role, ref_id "
            "FROM stu_unified_users WHERE id = :i"), {"i": payload["prof_id"]}).mappings().first()
    except Exception:
        return None


def _resolve_instructor_code(db: Session, username: str, display_name: str,
                             ref_id=None):
    """teaching_preferences.instructor_code == old professors.id == ref_id."""
    if ref_id:
        return str(ref_id)
    # fallbacks (no ref_id): username, then cleaned-name match
    row = db.execute(text(
        "SELECT instructor_code FROM teaching_preferences "
        "WHERE instructor_username = :u LIMIT 1"), {"u": username}).first()
    if row:
        return row[0]
    nm = _clean(display_name)
    for sql in (
        "SELECT code, name FROM instructors",
        "SELECT DISTINCT instructor_code AS code, instructor_name AS name "
        "FROM teaching_preferences",
        "SELECT DISTINCT instructor_code AS code, instructor_name AS name "
        "FROM time_preferences",
    ):
        for r in db.execute(text(sql)).all():
            if r[0] and _clean(r[1]) == nm:
                return r[0]
    return None


def _require_user(request: Request, db: Session):
    u = _user_by_request(request, db)
    if not u:
        raise HTTPException(status_code=401, detail="نشست نامعتبر است")
    code = _resolve_instructor_code(db, u["username"], u["display_name"], u["ref_id"])
    return u, code


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/login")
def professor_login(body: LoginIn, db: Session = Depends(get_db)):
    username = (body.username or "").strip()
    password = body.password or ""
    if not username or not password:
        raise HTTPException(status_code=400, detail="نام کاربری و رمز عبور الزامی است")
    user = db.execute(text(
        "SELECT id, username, display_name, password_hash "
        "FROM stu_unified_users WHERE username = :u AND role = 'professor'"),
        {"u": username}).mappings().first()
    if not user:
        raise HTTPException(status_code=401, detail="نام کاربری یا رمز عبور اشتباه است")
    stored = user["password_hash"]
    if not stored:
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
    user, code = _require_user(request, db)
    prof_id = user["ref_id"]
    stats = {"instructor_code": code,
             "proposals_total": 0, "proposals_pending": 0,
             "availability_slots": 0, "max_units": None}
    if code:
        stats["proposals_total"] = db.execute(text(
            "SELECT COUNT(*) FROM teaching_preferences WHERE instructor_code = :c"),
            {"c": str(code)}).scalar() or 0
        stats["proposals_pending"] = db.execute(text(
            "SELECT COUNT(*) FROM teaching_preferences "
            "WHERE instructor_code = :c AND status = 'pending'"),
            {"c": str(code)}).scalar() or 0
        stats["availability_slots"] = db.execute(text(
            "SELECT COUNT(*) FROM time_preferences WHERE instructor_code = :c"),
            {"c": str(code)}).scalar() or 0
        stats["max_units"] = db.execute(text(
            "SELECT max_teaching_units FROM instructors WHERE code = :c"),
            {"c": str(code)}).scalar()
    return {"user": {"id": user["id"], "username": user["username"],
                     "full_name": user["display_name"], "prof_id": prof_id,
                     "instructor_code": code},
            "stats": stats}


class PasswordIn(BaseModel):
    old_password: str = ""
    new_password: str


@router.post("/change-password")
def professor_change_password(body: PasswordIn, request: Request,
                              db: Session = Depends(get_db)):
    user, _ = _require_user(request, db)
    stored = user["password_hash"]
    if stored and not check_password_hash(stored, body.old_password):
        raise HTTPException(status_code=401, detail="رمز عبور فعلی اشتباه است")
    if len(body.new_password) < 4:
        raise HTTPException(status_code=422, detail="رمز جدید حداقل ۴ کاراکتر")
    db.execute(text("UPDATE stu_unified_users SET password_hash = :h WHERE id = :i"),
               {"h": generate_password_hash(body.new_password), "i": user["id"]})
    db.commit()
    return {"ok": True, "message": "رمز عبور تغییر کرد"}


# ==================== PROPOSALS (own) ====================

@router.get("/proposals")
def professor_proposals_list(request: Request, db: Session = Depends(get_db)):
    user, code = _require_user(request, db)
    if not code:
        return {"items": []}
    rows = db.execute(text(
        "SELECT id, unique_course_code, course_name, day_of_week, start_time, "
        "end_time, notes, status, term_code "
        "FROM teaching_preferences WHERE instructor_code = :c "
        "ORDER BY id DESC LIMIT 100"), {"c": str(code)}).mappings().all()
    return {"items": [dict(r) for r in rows]}


class ProposalIn(BaseModel):
    course_code: str
    term_code: str = "14051"
    day_of_week: str = ""
    start_time: str = ""
    end_time: str = ""
    notes: str = ""


@router.post("/proposals")
def professor_proposals_create(body: ProposalIn, request: Request,
                               db: Session = Depends(get_db)):
    user, code = _require_user(request, db)
    if not code:
        raise HTTPException(status_code=422, detail="کد استاد شما در سیستم یافت نشد")
    cc = str(body.course_code).strip()
    course = db.execute(text(
        "SELECT unique_title FROM unique_courses WHERE unique_code = :c LIMIT 1"),
        {"c": cc}).first()
    name = course[0] if course else cc
    dup = db.execute(text(
        "SELECT id FROM teaching_preferences WHERE instructor_code = :c "
        "AND unique_course_code = :cc AND term_code = :t LIMIT 1"),
        {"c": str(code), "cc": cc, "t": body.term_code}).first()
    if dup:
        raise HTTPException(status_code=409,
                            detail="این درس را قبلاً در این ترم پیشنهاد داده‌اید")
    db.execute(text(
        "INSERT INTO teaching_preferences (unique_course_code, course_name, "
        "instructor_code, instructor_name, instructor_username, status, term_code, "
        "day_of_week, start_time, end_time, notes) "
        "VALUES (:cc, :cn, :ic, :inm, :iu, 'pending', :t, :d, :st, :et, :n)"),
        {"cc": cc, "cn": name, "ic": str(code),
         "inm": user["display_name"], "iu": user["username"],
         "t": body.term_code, "d": body.day_of_week or None,
         "st": body.start_time or None, "et": body.end_time or None,
         "n": body.notes or None})
    db.commit()
    return {"ok": True, "message": f"پیشنهاد درس «{name}» ثبت شد"}


@router.delete("/proposals/{pref_id}")
def professor_proposals_delete(pref_id: int, request: Request,
                               db: Session = Depends(get_db)):
    user, code = _require_user(request, db)
    row = db.execute(text(
        "SELECT instructor_code FROM teaching_preferences WHERE id = :i"),
        {"i": pref_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="پیشنهاد یافت نشد")
    if str(row["instructor_code"]) != str(code):
        raise HTTPException(status_code=403, detail="فقط پیشنهاد خودتان قابل حذف است")
    db.execute(text("DELETE FROM teaching_preferences WHERE id = :i"), {"i": pref_id})
    db.commit()
    return {"ok": True, "deleted": pref_id}


# ==================== AVAILABILITY (own) ====================

@router.get("/availability")
def professor_availability_list(request: Request, db: Session = Depends(get_db)):
    user, code = _require_user(request, db)
    if not code:
        return {"items": []}
    rows = db.execute(text(
        "SELECT id, day, start_time, end_time, time_group, priority, status "
        "FROM time_preferences WHERE instructor_code = :c "
        "ORDER BY id LIMIT 200"), {"c": str(code)}).mappings().all()
    return {"items": [dict(r) for r in rows]}


class AvailIn(BaseModel):
    day: str
    start_time: str
    end_time: str
    time_group: str = ""
    priority: int = 2


@router.post("/availability")
def professor_availability_create(body: AvailIn, request: Request,
                                  db: Session = Depends(get_db)):
    user, code = _require_user(request, db)
    if not code:
        raise HTTPException(status_code=422, detail="کد استاد شما در سیستم یافت نشد")
    meta = db.execute(text(
        "SELECT cooperation_type, expert_group FROM time_preferences "
        "WHERE instructor_code = :c LIMIT 1"), {"c": str(code)}).mappings().first()
    coop = meta["cooperation_type"] if meta else ""
    grp = meta["expert_group"] if meta else ""
    tg = body.time_group or ("morning" if body.start_time < "12:00" else "afternoon")
    db.execute(text(
        "INSERT INTO time_preferences (day, cooperation_type, end_time, expert_group, "
        "status, instructor_code, instructor_name, instructor_username, start_time, "
        "time_group, priority) "
        "VALUES (:d, :coop, :et, :grp, 1, :c, :nm, :iu, :st, :tg, :pr)"),
        {"d": body.day, "coop": coop, "et": body.end_time, "grp": grp,
         "c": str(code), "nm": user["display_name"], "iu": user["username"],
         "st": body.start_time, "tg": tg, "pr": body.priority})
    db.commit()
    return {"ok": True, "message": "بازه دسترس‌بازی ثبت شد"}


@router.delete("/availability/{slot_id}")
def professor_availability_delete(slot_id: int, request: Request,
                                  db: Session = Depends(get_db)):
    user, code = _require_user(request, db)
    row = db.execute(text(
        "SELECT instructor_code FROM time_preferences WHERE id = :i"),
        {"i": slot_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="بازه یافت نشد")
    if str(row["instructor_code"]) != str(code):
        raise HTTPException(status_code=403, detail="فقط بازه خودتان قابل حذف است")
    db.execute(text("DELETE FROM time_preferences WHERE id = :i"), {"i": slot_id})
    db.commit()
    return {"ok": True, "deleted": slot_id}


# ==================== COURSE OPTIONS (for pickers) ====================

@router.get("/course-options")
def professor_course_options(db: Session = Depends(get_db)):
    rows = db.execute(text(
        "SELECT MIN(id) AS id, unique_code AS code, unique_title AS title "
        "FROM unique_courses WHERE is_active = 1 "
        "GROUP BY unique_code, unique_title ORDER BY unique_title")).mappings().all()
    return {"items": [dict(r) for r in rows]}


# ==================== STATS ====================

@router.get("/stats")
def professor_stats(request: Request, db: Session = Depends(get_db)):
    user, code = _require_user(request, db)
    out = {"current_classes": 0, "total_students": 0, "active_proposals": 0,
           "avg_fill_rate": 0}
    if user["ref_id"]:
        try:
            old = sqlite3.connect(r"E:\course-scheduling\backend\schedule.db")
            old.row_factory = sqlite3.Row
            secs = old.execute(
                "SELECT registered_count, capacity FROM class_sections "
                "WHERE professor_id = ?", (user["ref_id"],)).fetchall()
            out["current_classes"] = len(secs)
            out["total_students"] = sum(s["registered_count"] or 0 for s in secs)
            rates = [((s["registered_count"] or 0) / s["capacity"]) * 100
                     for s in secs if s["capacity"]]
            out["avg_fill_rate"] = round(sum(rates) / len(rates), 1) if rates else 0
            old.close()
        except Exception:
            pass
    if code:
        out["active_proposals"] = db.execute(text(
            "SELECT COUNT(*) FROM teaching_preferences "
            "WHERE instructor_code = :c AND status = 'pending'"),
            {"c": str(code)}).scalar() or 0
    return out
