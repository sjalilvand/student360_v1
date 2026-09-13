# app/services/risk_service.py
# Academic Risk Prediction (Phase 2 / category 14: early warning).
# Hybrid design: transparent weighted factors now (tiny pilot data) +
# ML-ready interface (swap in RandomForest when history grows).
# Document rules: warning includes reason + severity + suggested action;
# never triggers automatic punitive decisions.
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services import behavioral_service as bs

WEIGHTS = {"gpa": 30, "trend": 20, "failed": 20, "probation": 20, "engagement": 10}


def _gpa_band_score(gpa):
    if gpa is None:
        return 15, "معدل نامشخص (داده نمره کافی نیست)"
    if gpa >= 16:
        return 0, None
    if gpa >= 14:
        return 8, f"معدل {gpa} در محدوده متوسط است"
    if gpa >= 12:
        return 16, f"معدل {gpa} نزدیک به مرز مشروطی است"
    if gpa >= 10:
        return 24, f"معدل {gpa} پایین است"
    return 30, f"معدل {gpa} زیر حداقل نصاب (۱۲) است"


def _trend_score(term_gpas):
    if len(term_gpas) < 2:
        return 5, "برای ارزیابی روند، نمره نیمسال بیشتری لازم است"
    prev, last = float(term_gpas[-2][1]), float(term_gpas[-1][1])
    drop = prev - last
    if drop <= 0:
        return 0, None
    if drop < 2:
        return 8, f"معدل آخرین نیمسال {round(drop, 2)} واحد نسبت به قبل کاهش یافته"
    if drop <= 4:
        return 14, f"افت معدل {round(drop, 2)} واحدی در آخرین نیمسال"
    return 20, f"افت شدید معدل ({round(drop, 2)} واحد) در آخرین نیمسال"


def compute_risk(db: Session, student_number: str, student_name: str = None) -> dict:
    gpa = None
    try:
        gpa_row = db.execute(text(
            "SELECT weighted_gpa, total_credits FROM v_student_gpa WHERE student_number = :sn"),
            {"sn": student_number}).mappings().first()
        if gpa_row and gpa_row["weighted_gpa"] is not None:
            gpa = float(gpa_row["weighted_gpa"])
    except Exception:
        # marts not built yet (fresh install) -> compute directly from grades
        try:
            _g = db.execute(text(
                "SELECT ROUND(SUM(g.grade * g.credits) * 1.0 / NULLIF(SUM(g.credits), 0), 2) "
                "FROM stu_grades g JOIN stu_students s ON s.id = g.student_id "
                "WHERE s.student_number = :sn AND g.grade IS NOT NULL"),
                {"sn": student_number}).scalar()
            gpa = float(_g) if _g is not None else None
        except Exception:
            gpa = None

    term_gpas = db.execute(text(
        "SELECT g.term, ROUND(SUM(g.grade * g.credits) * 1.0 / NULLIF(SUM(g.credits), 0), 2) AS tg "
        "FROM stu_grades g JOIN stu_students s ON s.id = g.student_id "
        "WHERE s.student_number = :sn AND g.grade IS NOT NULL "
        "GROUP BY g.term ORDER BY g.term"), {"sn": student_number}).all()

    failed_credits = db.execute(text(
        "SELECT COALESCE(SUM(g.credits), 0) FROM stu_grades g "
        "JOIN stu_students s ON s.id = g.student_id "
        "WHERE s.student_number = :sn AND g.status = 'failed'"),
        {"sn": student_number}).scalar() or 0

    probation = db.execute(text(
        "SELECT COALESCE(MAX(a.probation_count), 0) FROM stu_academic_statuses a "
        "JOIN stu_students s ON s.id = a.student_id WHERE s.student_number = :sn"),
        {"sn": student_number}).scalar() or 0

    eng = bs.engagement_index(db, student_number, days=30)
    eng_score = eng.get("score", 0)

    factors, reasons, actions = {}, [], []

    s, why = _gpa_band_score(gpa)
    factors["gpa"] = s
    if why:
        reasons.append(why)
        actions.append("برنامه مطالعه منظم + استفاده از «کوییز هوشمند» و «استاد هوشمند» برای دروس ضعیف")

    s, why = _trend_score(term_gpas)
    factors["trend"] = s
    if why:
        reasons.append(why)
        actions.append("با کارشناس آموزش درباره علت افت نمرات گفتگو کنید")

    if failed_credits <= 0:
        factors["failed"] = 0
    else:
        factors["failed"] = 8 if failed_credits <= 4 else (14 if failed_credits <= 9 else 20)
        reasons.append(f"{failed_credits} واحد مردودی در کارنامه")
        actions.append("برای جبران دروس مردودی با مشاور تحصیلی برنامه‌ریزی کنید")

    if probation <= 0:
        factors["probation"] = 0
    else:
        factors["probation"] = 10 if probation == 1 else (15 if probation == 2 else 20)
        reasons.append(f"سابقه {probation} بار مشروطی")
        actions.append("حجم واحد ترم آینده را با نظر کارشناس تنظیم کنید")

    if eng_score >= 50:
        factors["engagement"] = 0
    elif eng_score >= 25:
        factors["engagement"] = 4
        reasons.append(f"تعامل با سامانه متوسط است (شاخص {eng_score})")
    else:
        factors["engagement"] = 10
        reasons.append(f"تعامل با سامانه پایین است (شاخص {eng_score})")
        actions.append("از تقویم، هشدارها و دستیار انتخاب واحد به‌طور منظم استفاده کنید")

    total = min(sum(factors.values()), 100)
    level = ("بالا" if total >= 60 else "متوسط" if total >= 35 else "پایین")

    return {
        "student_number": student_number,
        "student_name": student_name,
        "risk_score": total,
        "risk_level": level,
        "factors": factors,
        "weights": WEIGHTS,
        "reasons": reasons,
        "suggested_actions": list(dict.fromkeys(actions)),
        "gpa": gpa,
        "failed_credits": int(failed_credits),
        "probation_count": int(probation),
        "engagement_score": eng_score,
        "disclaimer": ("⚠️ این پیش‌بینی اولیه و غیرقطعی است؛ مبنای هیچ تصمیم تنبیهی "
                       "خودکار نیست و فقط برای هشدار زودهنگام و حمایت است."),
    }


def list_risks(db: Session, limit: int = 50) -> list:
    students = db.execute(text(
        "SELECT student_number, TRIM(first_name || ' ' || last_name) AS full_name "
        "FROM stu_students ORDER BY student_number")).all()
    out = []
    for sn, name in students:
        try:
            out.append(compute_risk(db, sn, name))
        except Exception:
            continue
    out.sort(key=lambda x: -x["risk_score"])
    return out[: max(1, min(int(limit), 200))]

