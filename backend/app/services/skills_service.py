# app/services/skills_service.py
# Skill extraction + career readiness (Phase 2 / category 13).
# Deterministic keyword engine + optional LLM enrichment (cached).
from __future__ import annotations

import json
import re

from sqlalchemy import inspect as sa_inspect, text
from sqlalchemy.orm import Session

from app.models.skills import StuCourseSkill
from app.services import event_tracking_service as ets

SKILL_DEFS = [
    {"name": "برنامه‌نویسی", "kw": ("برنامه نویسی", "برنامه سازی", "پایتون", "python", "java", "c++", "مبانی کامپیوتر")},
    {"name": "الگوریتم و ساختار داده", "kw": ("الگوریتم", "ساختمان داده", "ساختار داده", "گسسته")},
    {"name": "پایگاه داده", "kw": ("دیتابیس", "پایگاه داده", "database", "sql")},
    {"name": "توسعه وب", "kw": ("وب", "web", "طراحی صفحات", "javascript")},
    {"name": "هوش مصنوعی", "kw": ("هوش مصنوعی", "هوش محاسباتی", "یادگیری ماشین", "machine learning", "بینایی", "پردازش تصویر", "پردازش زبان", "nlp")},
    {"name": "سیستم‌های عامل", "kw": ("سیستم عامل", "سیستم‌عامل", "operating system")},
    {"name": "شبکه", "kw": ("شبکه", "network")},
    {"name": "امنیت", "kw": ("امنیت", "security", "رمزنگاری")},
    {"name": "ریاضیات و آمار", "kw": ("ریاضی", "آمار", "احتمال", "معادلات دیفرانسیل", "جبر خطی")},
    {"name": "مهندسی نرم‌افزار", "kw": ("مهندسی نرم‌افزار", "تحلیل و طراحی", "الگوهای طراحی")},
    {"name": "تجربه عملی", "kw": ("کارآموزی", "کارورزی", "پروژه", "internship")},
]
SKILL_NAMES = [d["name"] for d in SKILL_DEFS]

CAREER_TRACKS = [
    {"name": "توسعه‌دهنده بک‌اند", "required": ["برنامه‌نویسی", "پایگاه داده", "الگوریتم و ساختار داده", "سیستم‌های عامل", "مهندسی نرم‌افزار"]},
    {"name": "توسعه‌دهنده وب", "required": ["توسعه وب", "برنامه‌نویسی", "پایگاه داده", "تجربه عملی"]},
    {"name": "مهندس داده", "required": ["پایگاه داده", "ریاضیات و آمار", "برنامه‌نویسی", "هوش مصنوعی"]},
    {"name": "متخصص هوش مصنوعی", "required": ["هوش مصنوعی", "ریاضیات و آمار", "الگوریتم و ساختار داده", "برنامه‌نویسی"]},
    {"name": "کارشناس شبکه و امنیت", "required": ["شبکه", "امنیت", "سیستم‌های عامل", "الگوریتم و ساختار داده"]},
]

_LEVEL_ORDER = {"قوی": 0, "متوسط": 1, "پایه": 2, "در حال یادگیری": 3}
_LEVEL_WEIGHT = {"قوی": 1.0, "متوسط": 0.7, "پایه": 0.5, "در حال یادگیری": 0.3}

DISCLAIMER = ("⚠️ این پروفایل شغلی تحلیلی اولیه است و جایگزین مشاوره شغلی رسمی نیست.")


def career_readiness(db: Session, sn: str) -> dict:
    """Public alias - readiness view of the skill profile."""
    return student_skill_profile(db, sn)


def _norm(s):
    return (s or "").lower().replace("\u200c", " ").strip()


def keyword_skills(title):
    t = _norm(title)
    out = []
    for d in SKILL_DEFS:
        if any(kw in t for kw in d["kw"]):
            out.append(d["name"])
    return out


def ensure_course_skills(db: Session, course_code, title):
    row = db.query(StuCourseSkill).filter(
        StuCourseSkill.course_code == str(course_code)).first()
    if row:
        try:
            return json.loads(row.skills or "[]"), row.source
        except Exception:
            pass
    skills = keyword_skills(title)
    db.add(StuCourseSkill(course_code=str(course_code),
                          skills=json.dumps(skills, ensure_ascii=False),
                          source="keyword"))
    db.commit()
    return skills, "keyword"


def _llm_skills(db: Session, title):
    from app.services import llm_client as lc
    user = (f"عنوان درس دانشگاهی: {title}\n"
            f"فهرست مجاز مهارت‌ها: {json.dumps(SKILL_NAMES, ensure_ascii=False)}\n"
            "فقط JSON آرایه‌ای از مهارت‌های مرتبط برگردان (زیرمجموعه فهرست).")
    raw = lc.llm_chat("فقط JSON آرایه خالص برگردان؛ بدون هیچ متن اضافه.", user)
    if not raw:
        return None
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if not m:
        return None
    try:
        arr = json.loads(m.group(0))
        return [x for x in arr if x in SKILL_NAMES]
    except Exception:
        return None


def enrich_courses(db: Session, limit: int = 6) -> dict:
    """LLM extraction for curriculum courses the keyword engine could not map."""
    cols = [c["name"] for c in sa_inspect(db.bind).get_columns("stu_curriculum")] if True else []
    code_c = next((c for c in ("course_code", "code", "unique_code") if c in cols), None)
    title_c = next((c for c in ("course_title", "title", "name") if c in cols), None)
    if not code_c:
        return {"enriched": [], "detail": "curriculum unavailable"}
    rows = db.execute(text(f"SELECT DISTINCT {code_c} AS cc, {title_c or code_c} AS tt "
                           "FROM stu_curriculum")).mappings().all()
    enriched, scanned = [], 0
    for r in rows:
        if scanned >= max(1, min(int(limit), 20)):
            break
        cc, tt = str(r["cc"] or "").strip(), str(r["tt"] or "").strip()
        if not cc or not tt:
            continue
        row = db.query(StuCourseSkill).filter(StuCourseSkill.course_code == cc).first()
        if row and row.source == "llm":
            continue
        if row and row.skills not in ("[]", ""):
            continue
        scanned += 1
        sk = _llm_skills(db, tt)
        if sk:
            if row:
                row.skills = json.dumps(sk, ensure_ascii=False)
                row.source = "llm"
            else:
                db.add(StuCourseSkill(course_code=cc, skills=json.dumps(sk, ensure_ascii=False),
                                      source="llm"))
            db.commit()
            enriched.append({"course_code": cc, "title": tt, "skills": sk})
    return {"scanned": scanned, "enriched": enriched}


def student_skill_profile(db: Session, sn: str) -> dict:
    sn = str(sn)
    s = db.execute(text("SELECT id, first_name, last_name FROM stu_students "
                        "WHERE student_number = :sn"), {"sn": sn}).mappings().first()
    if not s:
        return {"error": "student not found"}

    grades = db.execute(text(
        "SELECT course_code, course_title, grade, status FROM stu_grades "
        "WHERE student_id = :sid"), {"sid": s["id"]}).mappings().all()
    best = {}
    for g in grades:
        code = str(g["course_code"] or "").strip()
        if not code:
            continue
        cur = best.get(code)
        if cur is None or (g["grade"] or 0) > (cur["grade"] or 0):
            best[code] = dict(g)
    passed = {c: g for c, g in best.items()
              if g["status"] == "passed" or (g["grade"] is not None and g["grade"] >= 10)}
    inprog = db.execute(text(
        "SELECT course_code, course_title FROM stu_enrollments "
        "WHERE student_id = :sid AND status = 'current'"), {"sid": s["id"]}).mappings().all()

    skill_courses = {}

    def add(skill, code, title, grade, phase):
        skill_courses.setdefault(skill, []).append(
            {"code": code, "title": title, "grade": grade, "phase": phase})

    for code, g in passed.items():
        for sk in ensure_course_skills(db, code, g["course_title"])[0]:
            add(sk, code, g["course_title"], g["grade"], "passed")
    for e in inprog:
        for sk in ensure_course_skills(db, str(e["course_code"]), e["course_title"])[0]:
            add(sk, str(e["course_code"]), e["course_title"], None, "in_progress")

    skills_out = []
    for name in SKILL_NAMES:
        items = skill_courses.get(name, [])
        if not items:
            continue
        pitems = [i for i in items if i["phase"] == "passed"]
        if pitems:
            avg = sum((i["grade"] or 0) for i in pitems) / len(pitems)
            level = "قوی" if avg >= 17 else ("متوسط" if avg >= 14 else "پایه")
        else:
            avg, level = None, "در حال یادگیری"
        skills_out.append({"name": name, "level": level,
                           "avg_grade": round(avg, 1) if avg is not None else None,
                           "courses": [i["code"] for i in items]})
    skills_out.sort(key=lambda x: _LEVEL_ORDER[x["level"]])

    levels = {x["name"]: x["level"] for x in skills_out}
    tracks = []
    for t in CAREER_TRACKS:
        got = [_LEVEL_WEIGHT.get(levels.get(r), 0.0) for r in t["required"]]
        readiness = round(100 * sum(got) / len(t["required"])) if t["required"] else 0
        gaps = [r for r in t["required"] if levels.get(r) is None]
        weak = [r for r in t["required"] if levels.get(r) in ("پایه",)]
        tracks.append({"name": t["name"], "readiness_pct": readiness,
                       "gaps": gaps, "weak": weak,
                       "have": [r for r in t["required"] if levels.get(r)]})
    tracks.sort(key=lambda x: -x["readiness_pct"])

    try:
        ets.track_event(db, event_type="career_viewed", event_name="me",
                        student_ref=sn, source="api",
                        payload={"skills": len(skills_out),
                                 "top_track": tracks[0]["name"] if tracks else None})
    except Exception:
        pass

    return {"student_number": sn,
            "student_name": ((s["first_name"] or "") + " " + (s["last_name"] or "")).strip(),
            "skills": skills_out, "tracks": tracks,
            "top_track": tracks[0] if tracks else None,
            "disclaimer": DISCLAIMER}


def recommended_courses_for(db: Session, sn: str, track_name: str, limit: int = 5) -> list:
    """Remaining curriculum courses that map to the track's missing skills."""
    track = next((t for t in CAREER_TRACKS if t["name"] == track_name), None)
    if not track:
        return []
    prof = student_skill_profile(db, sn)
    if prof.get("error"):
        return []
    have = {x["name"] for x in prof["skills"]}
    needed = [r for r in track["required"] if r not in have]
    if not needed:
        return []
    s = db.execute(text("SELECT id, program_id FROM stu_students WHERE student_number=:sn"),
                   {"sn": str(sn)}).mappings().first()
    if not s or not s["program_id"]:
        return []
    grades = db.execute(text("SELECT course_code FROM stu_grades WHERE student_id=:sid"),
                        {"sid": s["id"]}).mappings().all()
    done = {str(g["course_code"]).strip() for g in grades}
    rows = db.execute(text(
        "SELECT course_code, course_title FROM stu_curriculum WHERE program_id = :pid"),
        {"pid": s["program_id"]}).mappings().all()
    out = []
    for r in rows:
        cc, tt = str(r["course_code"] or "").strip(), str(r["course_title"] or "").strip()
        if cc in done:
            continue
        sks = ensure_course_skills(db, cc, tt)[0]
        hit = [x for x in sks if x in needed]
        if hit:
            out.append({"code": cc, "title": tt, "gives": hit})
        if len(out) >= max(1, min(int(limit), 10)):
            break
    return out

