# app/services/permission_service.py
from sqlalchemy import text

from app.core.database import SessionLocal
from app.models.permission import SysPermission

DEFAULT_MENUS = {
    "student": ["profile", "behavior", "studypath", "regulations", "guides",
                "selection", "graduation", "calendar", "alerts", "quiz",
                "adaptivequiz", "professor", "career", "twin", "ai"],
    "staff": ["overview", "students", "engagement", "risk", "interventions",
              "feedback", "graph", "votes", "ai"],
    "professor": ["profdash", "profproposals", "profavail", "profpass", "ai"],
}
ROLES = tuple(DEFAULT_MENUS.keys())


def seed_defaults(db):
    """Idempotent: create rows for every (role, menu) not present."""
    created = 0
    for role, menus in DEFAULT_MENUS.items():
        for mid in menus:
            exists = db.query(SysPermission).filter(
                SysPermission.role == role, SysPermission.menu_id == mid).first()
            if not exists:
                db.add(SysPermission(role=role, menu_id=mid, enabled=True))
                created += 1
    db.commit()
    return created


def menu_for_role(db, role: str):
    any_rows = db.query(SysPermission).filter(
        SysPermission.role == str(role)).count()
    rows = (db.query(SysPermission)
            .filter(SysPermission.role == str(role),
                    SysPermission.enabled == True)  # noqa: E712
            .all())
    if not any_rows:
        return {"role": role, "menus": DEFAULT_MENUS.get(role, []),
                "source": "default"}
    return {"role": role,
            "menus": [r.menu_id for r in rows if r.menu_id in DEFAULT_MENUS.get(role, [])],
            "source": "db"}


def matrix(db):
    out = {}
    for role, menus in DEFAULT_MENUS.items():
        rows = {r.menu_id: r.enabled for r in
                db.query(SysPermission).filter(SysPermission.role == role).all()}
        out[role] = [{"menu_id": m,
                      "enabled": rows.get(m, m in menus),
                      "known": True} for m in menus]
        # unknown/extra menu ids stored in db (e.g. after menu removal)
        extras = [r for r in db.query(SysPermission).filter(
            SysPermission.role == role).all() if r.menu_id not in menus]
        for e in extras:
            out[role].append({"menu_id": e.menu_id, "enabled": e.enabled,
                              "known": False})
    return out


def set_enabled(db, role: str, menu_id: str, enabled: bool) -> bool:
    if role not in ROLES:
        return False
    row = db.query(SysPermission).filter(
        SysPermission.role == role, SysPermission.menu_id == menu_id).first()
    if row:
        row.enabled = bool(enabled)
    else:
        db.add(SysPermission(role=role, menu_id=menu_id, enabled=bool(enabled)))
    db.commit()
    return True


def reset_role(db, role: str) -> bool:
    if role not in ROLES:
        return False
    db.query(SysPermission).filter(SysPermission.role == role).delete()
    for mid in DEFAULT_MENUS[role]:
        db.add(SysPermission(role=role, menu_id=mid, enabled=True))
    db.commit()
    return True


def ensure_seeded():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return seed_defaults(db)
    finally:
        db.close()
