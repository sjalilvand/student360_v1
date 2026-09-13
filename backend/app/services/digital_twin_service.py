# app/services/digital_twin_service.py
# Digital Twin "what-if" simulation (Phase 3 kickoff / row 2 of roadmap).
# Pure in-memory recompute over current state - NEVER writes student data.
from __future__ import annotations

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services import behavioral_service as bs
from app.services import event_tracking_service as ets
from app.services.risk_service import _gpa_band_score, _trend_score
from app.services.skills_service import keyword_skills
from app.services.study_path_service import _max_units

DISCLAIMER = ("⚠️ نتیجه شبیه‌سازی اولیه و غیرقطعی است؛ صرفاً برای برنامه‌ریزی است "
              "و مبنای هیچ تصمیم رسمی نیست.")

_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _fa(n):
    return str(n).translate(_PERSIAN_DIGITS)


def _failed_band(cr):
    if cr <= 0:
        return 0
    return 8 if cr <= 4 else (14 if cr <= 9 else 20)


def _probation_band(n):
    if n <= 0:
        return 0
    return 10 if n == 1 else (15 if n == 2 else 20)


def _engagement_band(score):
    if score >= 50:
        return 0
    return 4 if score >= 25 else 10


def _risk_from(gpa, term_gpas, failed_credits, probation, engagement):
    factors, reasons = {}, []
    s, why = _gpa_band_score(gpa)
    factors["gpa"] = s
    if why:
        reasons.append(why)
    s, why = _trend_score(term_gpas)
    factors["trend"] = s
    if why:
        reasons.append(why)
    factors["failed"] = _failed_band(failed_credits)
    factors["probation"] = _probation_band(probation)
    factors["engagement"] = _engagement_band(engagement)
    total = min(sum(factors.values()), 100)
    level = "بالا" if total >= 60 else ("متوسط" if total >= 35 else "پایین")
    return {"risk_score": total, "risk_level": level, "factors": factors,
            "reasons": reasons}


def _state(db: Session, sn: str):
    s = db.execute(text(
        "SELECT id, first_name, last_name FROM stu_students WHERE student_number = :sn"),
        {"sn": str(sn)}).mappings().first()
    if not s:
        return None
    grades = [dict(r) for r in db.execute(text(
        "SELECT term, course_code, course_title, credits, grade, status "
        "FROM stu_grades WHERE student_id = :sid"), {"sid": s["id"]}).mappings().all()]
    pts = sum((g["grade"] or 0) * g["credits"] for g in grades if g["grade"] is not None)
    crs = sum(g["credits"] for g in grades if g["grade"] is not None)
    gpa = round(pts / crs, 2) if crs else None

    tg_rows = db.execute(text(
        "SELECT g.term, ROUND(SUM(g.grade * g.credits) * 1.0 / NULLIF(SUM(g.credits), 0), 2) AS tg "
        "FROM stu_grades g JOIN stu_students s2 ON s2.id = g.student_id "
        "WHERE s2.student_number = :sn AND g.grade IS NOT NULL "
        "GROUP BY g.term ORDER BY g.term"), {"sn": str(sn)}).all()
    term_gpas = [(t, float(tg)) for t, tg in tg_rows if tg is not None]

    failed = db.execute(text(
        "SELECT COALESCE(SUM(g.credits), 0) FROM stu_grades g "
        "JOIN stu_students s2 ON s2.id = g.student_id "
        "WHERE s2.student_number = :sn AND g.status = 'failed'"),
        {"sn": str(sn)}).scalar() or 0
    probation = db.execute(text(
        "SELECT COALESCE(MAX(a.probation_count), 0) FROM stu_academic_statuses a "
        "JOIN stu_students s2 ON s2.id = a.student_id WHERE s2.student_number = :sn"),
        {"sn": str(sn)}).scalar() or 0
    engagement = bs.engagement_index(db, str(sn), days=30).get("score", 0)
    return {"student": s, "grades": grades, "gpa": gpa, "term_gpas": term_gpas,
            "failed_credits": int(failed), "probation": int(probation),
            "engagement": engagement}


def simulate(db: Session, sn: str, courses=None, units=None, avg_grade=None) -> dict:
    st = _state(db, sn)
    if not st:
        return {"error": "student not found", "student_number": str(sn)}

    risk_before = _risk_from(st["gpa"], st["term_gpas"], st["failed_credits"],
                             st["probation"], st["engagement"])
    cap_before, capr_before = _max_units(st["gpa"], st["probation"],
                                         risk_before["risk_level"])
    passed_units = sum(g["credits"] for g in st["grades"]
                       if (g["status"] == "passed") or (g["grade"] is not None and g["grade"] >= 10))

    # ---- normalize scenario ----
    courses = list(courses or [])
    if not courses and units and avg_grade:
        courses = [{"title": "ترم شبیه‌سازی",
                    "credits": int(units), "expected_grade": float(avg_grade)}]
    sim = []
    for c in courses:
        try:
            cr = max(1, min(int(c.get("credits") or 0), 24))
            gr_ = float(c.get("expected_grade"))
            gr_ = max(0.0, min(gr_, 20.0))
        except Exception:
            continue
        sim.append({"code": str(c.get("code") or "").strip(),
                    "title": str(c.get("title") or "درس شبیه‌سازی").strip()[:120],
                    "credits": cr, "expected_grade": round(gr_, 2)})
    if not sim:
        return {"error": "empty scenario — courses یا units+avg_grade بدهید"}

    sim_units = sum(c["credits"] for c in sim)
    term_gpa = round(sum(c["expected_grade"] * c["credits"] for c in sim) / sim_units, 2)
    sim_failed = sum(c["credits"] for c in sim if c["expected_grade"] < 10)

    pts = sum((g["grade"] or 0) * g["credits"] for g in st["grades"] if g["grade"] is not None)
    crs = sum(g["credits"] for g in st["grades"] if g["grade"] is not None)
    gpa_after = round((pts + sum(c["expected_grade"] * c["credits"] for c in sim))
                      / (crs + sim_units), 2) if (crs + sim_units) else None

    probation_after = st["probation"] + (1 if term_gpa is not None and term_gpa < 12 else 0)
    term_gpas_after = st["term_gpas"] + [(f"sim-{datetime.utcnow().year}", term_gpa)]
    failed_after = st["failed_credits"] + sim_failed

    risk_after = _risk_from(gpa_after, term_gpas_after, failed_after,
                            probation_after, st["engagement"])
    cap_after, capr_after = _max_units(gpa_after, probation_after,
                                       risk_after["risk_level"])

    warnings = []
    if sim_failed:
        warnings.append(f"{_fa(sim_failed)} واحد با نمره زیر ۱۰ در شبیه‌سازی مردود محسوب می‌شود.")
    if probation_after > st["probation"]:
        warnings.append("معدل ترم شبیه‌سازی زیر ۱۲ است → یک مشروطی اضافه می‌شود (آیین‌نامه).")
    if term_gpa is not None and term_gpa >= 17:
        warnings.append("ترم عالی! شرط ممتاز (سقف ۲۴) در ترم‌های بعد باز می‌شود.")
    if sim_units > cap_before:
        warnings.append(f"واحد سناریو ({_fa(sim_units)}) از سقف فعلی ({_fa(cap_before)}) بیشتر است.")

    skill_preview = {}
    for c in sim:
        sk = keyword_skills(c["title"])
        if sk:
            skill_preview[c["title"]] = sk

    try:
        ets.track_event(db, event_type="twin_simulated", event_name="me",
                        student_ref=str(sn), source="api",
                        payload={"units": sim_units, "term_gpa": term_gpa,
                                 "risk_before": risk_before["risk_score"],
                                 "risk_after": risk_after["risk_score"]})
    except Exception:
        pass

    return {
        "scenario": {"courses": sim, "units": sim_units, "term_gpa": term_gpa},
        "before": {"gpa": st["gpa"], "probation_count": st["probation"],
                   "max_units": cap_before, "cap_reasons": capr_before,
                   "risk_score": risk_before["risk_score"],
                   "risk_level": risk_before["risk_level"],
                   "passed_units": passed_units,
                   "failed_credits": st["failed_credits"]},
        "after": {"gpa": gpa_after, "probation_count": probation_after,
                  "max_units": cap_after, "cap_reasons": capr_after,
                  "risk_score": risk_after["risk_score"],
                  "risk_level": risk_after["risk_level"],
                  "failed_credits": failed_after},
        "deltas": {"gpa": (round(gpa_after - st["gpa"], 2)
                           if (gpa_after is not None and st["gpa"] is not None) else None),
                   "risk": risk_after["risk_score"] - risk_before["risk_score"],
                   "max_units": cap_after - cap_before},
        "warnings": warnings,
        "skill_preview": skill_preview,
        "risk_after_reasons": risk_after["reasons"],
        "disclaimer": DISCLAIMER,
    }

