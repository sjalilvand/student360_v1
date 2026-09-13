# Student 360 — academic engine: course selection assistant (STU-CRS-01..11),
# prerequisite analysis (بند ۸-۶) and graduation check (STU-GRD-01..09).
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models.student360 import (
    Program, Curriculum, Student, Grade, Enrollment, CourseRule, Term,
    CourseScenario, AcademicStatus,
)

# =====================================================================
# وضعیت‌های خروجی درس (بند ۸-۵)
# =====================================================================
STATUS_TAKABLE = "قابل اخذ"
STATUS_TAKABLE_WARNING = "قابل اخذ با اخطار"
STATUS_NEEDS_APPROVAL = "نیازمند تأیید آموزش"
STATUS_NOT_TAKABLE = "غیرقابل اخذ"
STATUS_SUGGESTED = "پیشنهادشده"
STATUS_CRITICAL = "ضروری برای جلوگیری از تأخیر تحصیلی"

PASS_GRADE = 10.0


# =====================================================================
# ابزارهای پایه
# =====================================================================

def _best_grades(db: Session, student_id: int) -> dict[str, Grade]:
    """بهترین نمره هر درس (برای کنترل قبولی قبلی — STU-CRS-05)."""
    grades = db.query(Grade).filter(Grade.student_id == student_id).all()
    best: dict[str, Grade] = {}
    for g in grades:
        cur = best.get(g.course_code)
        if cur is None or (g.grade or 0) > (cur.grade or 0):
            best[g.course_code] = g
    return best


def _passed_codes(best: dict[str, Grade]) -> set[str]:
    return {c for c, g in best.items() if g.status == "passed"}


def _active_rules(db: Session, today: date) -> dict[str, list[CourseRule]]:
    """قواعد فعال بر اساس تاریخ شروع/پایان اعتبار (قاعده ۹-۷)."""
    rules = db.query(CourseRule).all()
    by_course: dict[str, list[CourseRule]] = defaultdict(list)
    for r in rules:
        if r.effective_from and r.effective_from > today:
            continue
        if r.effective_to and r.effective_to < today:
            continue
        by_course[r.course_code].append(r)
    return by_course


def _is_probation(db: Session, student: Student) -> bool:
    row = (db.query(AcademicStatus)
           .filter(AcademicStatus.student_id == student.id)
           .order_by(AcademicStatus.term.desc())
           .first())
    return bool(row and row.status == "probation")


def _max_units(db: Session, student: Student, gpa: float) -> tuple[int, str]:
    """سقف واحد مجاز بر اساس معدل و وضعیت مشروطی (STU-CRS-03 و STU-CRS-06)."""
    if _is_probation(db, student):
        return 14, "وضعیت مشروطی: حداکثر ۱۴ واحد (مقررات مشروطی)"
    if gpa >= 17:
        return 24, "معدل ممتاز: تا ۲۴ واحد مجاز است"
    return 20, "سقف معمول ۲۰ واحد"


# =====================================================================
# تحلیل پیش‌نیاز و هم‌نیاز (بند ۸-۶)
# =====================================================================

def analyze_course(db: Session, student: Student, course_code: str,
                   selected_codes: set[str] = None, rules: dict = None,
                   best: dict[str, Grade] = None) -> dict:
    """تحلیل کامل پیش‌نیاز/هم‌نیاز یک درس با دلیل مجاز/غیرمجاز بودن."""
    selected_codes = selected_codes or set()
    rules = rules or _active_rules(db, date.today())
    best = best or _best_grades(db, student.id)
    passed = _passed_codes(best)

    cur = db.query(Curriculum).filter(
        Curriculum.course_code == course_code).first()

    prereq_rows = [r for r in rules.get(course_code, [])
                   if r.rule_type == "prerequisite"]
    coreq_rows = [r for r in rules.get(course_code, [])
                  if r.rule_type == "corequisite"]
    exception_rows = [r for r in rules.get(course_code, [])
                      if r.rule_type == "exception" or r.is_exception]
    probation_rows = [r for r in rules.get(course_code, [])
                      if r.rule_type == "probation-restriction"]

    prereq_status = []
    ok_prereq = True
    for r in prereq_rows:
        code = r.related_course_code
        grade_row = best.get(code)
        status = "passed" if code in passed else (
            "in-progress" if code in selected_codes else "not-taken")
        # نمره درس پیش‌نیاز (بند ۸-۶)
        meets = code in passed and (r.min_grade is None or
                                    (grade_row and grade_row.grade >= r.min_grade))
        if not meets:
            ok_prereq = False
        prereq_status.append({
            "course_code": code, "status": status,
            "grade": grade_row.grade if grade_row else None,
            "min_grade": r.min_grade,
            "met": meets,
        })

    coreq_status = []
    ok_coreq = True
    for r in coreq_rows:
        code = r.related_course_code
        met = code in passed or code in selected_codes
        if not met:
            ok_coreq = False
        coreq_status.append({"course_code": code, "met": met})

    # اثر عدم اخذ درس بر نیمسال‌های بعد (بند ۸-۶)
    impact = []
    if cur and cur.is_chain_course and not ok_prereq:
        impact = ["عدم اخذ این درس باعث تأخیر یک نیمسالی در دروس زنجیره‌ای بعدی می‌شود."]

    has_exception = len(exception_rows) > 0
    allowed = ok_prereq and ok_coreq

    reasons = []
    if not ok_prereq:
        missing = [p["course_code"] for p in prereq_status if not p["met"]]
        reasons.append(f"پیش‌نیازهای گذرانده‌نشده: {', '.join(missing)}")
    if not ok_coreq:
        missing = [c["course_code"] for c in coreq_status if not c["met"]]
        reasons.append(f"هم‌نیازهای همراه‌نشده: {', '.join(missing)}")
    for p in probation_rows:
        reasons.append(p.restriction_detail or "محدودیت مشروطی فعال است.")

    return {
        "course_code": course_code,
        "course_title": cur.course_title if cur else course_code,
        "credits": cur.credits if cur else 3,
        "prerequisites": prereq_status,
        "corequisites": coreq_status,
        "exception": (exception_rows[0].exception_note if exception_rows else None),
        "has_exception": has_exception,
        "allowed": allowed or has_exception,
        "reasons": reasons,               # دلیل مجاز/غیرمجاز بودن (بند ۸-۶)
        "impact_if_not_taken": impact,
    }


# =====================================================================
# دستیار انتخاب واحد (بند ۸-۵)
# =====================================================================

def get_offered_courses(db: Session, term: str) -> list[dict]:
    """دروس قابل ارائه در نیمسال هدف (STU-CRS-07) — مبتنی بر چارت مصوب."""
    rows = db.query(Curriculum).all()
    return [
        {
            "course_code": r.course_code, "course_title": r.course_title,
            "credits": r.credits, "suggested_term": r.suggested_term,
            "course_nature": r.course_nature, "is_chain_course": r.is_chain_course,
        } for r in rows
    ]


def evaluate_course(db: Session, student: Student, course: dict,
                    selected_codes: set[str], selected_units: int,
                    gpa: float, rules: dict, best: dict[str, Grade]) -> dict:
    """ارزیابی یک درس برای انتخاب واحد با وضعیت و دلایل."""
    analysis = analyze_course(db, student, course["course_code"],
                              selected_codes, rules, best)
    reasons = list(analysis["reasons"])
    warnings = []
    needs_approval = False
    takable = True

    # STU-CRS-05: قبولی قبلی
    if course["course_code"] in _passed_codes(best):
        takable = False
        reasons.append("این درس قبلاً با موفقیت گذرانده شده است (تکرار مجاز نیست).")

    # STU-CRS-02: پیش‌نیاز/هم‌نیاز
    if not analysis["allowed"]:
        if analysis["has_exception"]:
            needs_approval = True
            warnings.append("دارای استثنای ثبت‌شده؛ نیازمند تأیید آموزش.")
        else:
            takable = False

    # STU-CRS-03: سقف واحد
    max_units, max_reason = _max_units(db, student, gpa)
    if selected_units + course["credits"] > max_units:
        takable = False
        reasons.append(f"افزودن این درس سقف واحد ({max_units}) را نقض می‌کند. {max_reason}")

    # STU-CRS-06: محدودیت مشروطی
    if _is_probation(db, student):
        for r in rules.get(course["course_code"], []):
            if r.rule_type == "probation-restriction":
                warnings.append(r.restriction_detail or "محدودیت مشروطی فعال است.")

    # وضعیت نهایی (خروجی بند ۸-۵)
    if not takable:
        status = STATUS_NOT_TAKABLE
    elif needs_approval:
        status = STATUS_NEEDS_APPROVAL
    elif warnings:
        status = STATUS_TAKABLE_WARNING
    else:
        status = STATUS_TAKABLE

    return {
        "course_code": course["course_code"],
        "course_title": course["course_title"],
        "credits": course["credits"],
        "suggested_term": course["suggested_term"],
        "course_nature": course["course_nature"],
        "status": status,
        "reasons": reasons,          # STU-CRS-09 — دلیل پیشنهاد یا عدم پیشنهاد
        "warnings": warnings,
        "analysis": analysis,
    }


def build_selection_assistant(db: Session, student: Student, target_term: str) -> dict:
    """خروجی کامل دستیار انتخاب واحد برای نیمسال آینده (STU-CRS-01..09)."""
    gpas = compute_simple_gpa(db, student.id)
    gpa = gpas["overall"]
    best = _best_grades(db, student.id)
    passed = _passed_codes(best)
    rules = _active_rules(db, date.today())

    # نیمسال هدف باید برای انتخاب واحد باز باشد (STU-CRS-07)
    term_row = db.query(Term).filter(Term.code == target_term).first()
    term_open = bool(term_row and term_row.is_open_for_registration)

    current_units = sum(e.credits for e in db.query(Enrollment).filter(
        Enrollment.student_id == student.id, Enrollment.status == "current").all())
    in_progress_codes = {e.course_code for e in db.query(Enrollment).filter(
        Enrollment.student_id == student.id, Enrollment.status == "current").all()}

    max_units, max_reason = _max_units(db, student, gpa)

    courses = get_offered_courses(db, target_term)
    results = []
    for c in courses:
        if c["course_code"] in in_progress_codes:
            continue  # درس جاری دوباره پیشنهاد نمی‌شود
        ev = evaluate_course(db, student, c, in_progress_codes, 0, gpa, rules, best)
        results.append(ev)

    # STU-CRS-08: اولویت دروس ضروری و زنجیره‌ای
    for ev in results:
        cur = db.query(Curriculum).filter(
            Curriculum.course_code == ev["course_code"]).first()
        if ev["status"] in (STATUS_TAKABLE, STATUS_TAKABLE_WARNING):
            # اولویت: درس عقب‌افتاده از چارت یا زنجیره‌ای
            expected_term = cur.suggested_term if cur else None
            passed_terms = _estimate_current_term(student, passed)
            if cur and cur.is_chain_course:
                ev["status"] = STATUS_CRITICAL if (expected_term and
                                                   expected_term <= passed_terms + 1) else ev["status"]
                if ev["status"] == STATUS_CRITICAL:
                    ev["reasons"].insert(0, "درس زنجیره‌ای: تأخیر در اخذ آن باعث عقب‌افتادگی تحصیلی می‌شود.")
            if expected_term and expected_term <= passed_terms:
                if ev["status"] == STATUS_TAKABLE:
                    ev["reasons"].insert(0, "این درس طبق چارت باید تاکنون گذرانده می‌شد؛ در اولویت پیشنهاد است.")

    # پیشنهادهای خودکار: دروس بحرانی/اولویت‌دار تا سقف واحد
    suggested_units = 0
    suggestions = []
    priority = [ev for ev in results
                if ev["status"] in (STATUS_CRITICAL, STATUS_TAKABLE, STATUS_TAKABLE_WARNING)]
    priority.sort(key=lambda e: (
        0 if e["status"] == STATUS_CRITICAL else 1,
        e["suggested_term"] or 9))
    for ev in priority:
        if suggested_units + ev["credits"] <= max_units:
            suggestions.append(ev["course_code"])
            suggested_units += ev["credits"]
    for ev in results:
        if ev["course_code"] in suggestions:
            ev["status"] = STATUS_SUGGESTED

    return {
        "target_term": target_term,
        "term_open": term_open,
        "gpa": gpa,
        "max_units": max_units,
        "max_units_reason": max_reason,
        "current_units_in_progress": current_units,
        "courses": results,                 # STU-CRS-01 با وضعیت‌های شش‌گانه
        "suggested_course_codes": suggestions,   # STU-CRS-08
        "suggested_units": suggested_units,
        "note": ("ثبت نهایی فقط در سامانه رسمی آموزش انجام می‌شود؛ "
                 "این فهرست صرفاً پیشنهاد است (STU-CRS-11)."),
    }


def _estimate_current_term(student: Student, passed: set[str]) -> int:
    """تخمین ترم جاری دانشجو بر اساس ورودی."""
    try:
        entry_year = int(student.entry_year or student.entry_term.split("-")[0])
    except (ValueError, IndexError):
        return 1
    now_year = date.today().year - 621  # تقریب شمسی
    elapsed = max(now_year - entry_year, 0)
    return min(elapsed * 2 + 1, 8)


def compute_simple_gpa(db: Session, student_id: int) -> dict:
    grades = db.query(Grade).filter(
        Grade.student_id == student_id, Grade.grade.isnot(None)).all()
    if not grades:
        return {"overall": 0.0, "last_term": None, "last_term_gpa": None}
    total_points = sum((g.grade or 0) * g.credits for g in grades)
    total_units = sum(g.credits for g in grades)
    last_term = max(g.term for g in grades)
    last = [g for g in grades if g.term == last_term]
    last_pts = sum((g.grade or 0) * g.credits for g in last)
    last_units = sum(g.credits for g in last)
    return {
        "overall": round(total_points / total_units, 2),
        "last_term": last_term,
        "last_term_gpa": round(last_pts / last_units, 2) if last_units else None,
    }


# =====================================================================
# سناریوهای انتخاب واحد (STU-CRS-10) و کنترل‌های سبد
# =====================================================================

def _time_to_minutes(t: str) -> int:
    try:
        h, m = t.split(":")
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError):
        return 0


def validate_scenario(db: Session, student: Student, target_term: str,
                      course_codes: list[str]) -> dict:
    """کنترل‌های STU-CRS-02..07 برای یک سبد انتخابی."""
    best = _best_grades(db, student.id)
    passed = _passed_codes(best)
    rules = _active_rules(db, date.today())
    gpa = compute_simple_gpa(db, student.id)["overall"]
    in_progress = {e.course_code for e in db.query(Enrollment).filter(
        Enrollment.student_id == student.id, Enrollment.status == "current").all()}

    errors, warnings = [], []
    total_units = 0
    time_slots = []

    # STU-CRS-03: سقف و کف
    max_units, max_reason = _max_units(db, student, gpa)
    cur_rows = {c.course_code: c for c in db.query(Curriculum).all()}
    for code in course_codes:
        cur = cur_rows.get(code)
        if not cur:
            errors.append(f"درس {code} در چارت مصوب یافت نشد.")
            continue
        total_units += cur.credits

        # STU-CRS-05: قبولی قبلی
        if code in passed:
            errors.append(f"درس {cur.course_title} قبلاً گذرانده شده است.")
            continue
        if code in in_progress:
            errors.append(f"درس {cur.course_title} در نیمسال جاری در حال اخذ است.")

        # STU-CRS-02: پیش‌نیاز
        analysis = analyze_course(db, student, code,
                                  in_progress | set(course_codes) - {code},
                                  rules, best)
        if not analysis["allowed"] and not analysis["has_exception"]:
            errors.append(f"درس {cur.course_title}: {'؛ '.join(analysis['reasons'])}")
        elif analysis["has_exception"] and not analysis["allowed"]:
            warnings.append(f"درس {cur.course_title}: نیازمند تأیید آموزش (استثنا).")

        # هم‌نیاز داخل سبد
        for r in rules.get(code, []):
            if r.rule_type == "corequisite":
                if r.related_course_code not in course_codes and \
                   r.related_course_code not in passed:
                    errors.append(
                        f"درس {cur.course_title} هم‌نیاز {r.related_course_code} را نیازمند است.")

        # STU-CRS-04: تداخل زمانی (بر اساس برنامه هفتگی ثبت‌شده در Enrollment های نمونه)
        day = _course_day_hint(db, student, code, target_term)
        start, end = _course_time_hint(db, student, code, target_term)
        if day is not None and start and end:
            time_slots.append((code, day, _time_to_minutes(start), _time_to_minutes(end)))

    # تداخل زمانی داخل سبد
    for i in range(len(time_slots)):
        for j in range(i + 1, len(time_slots)):
            a, b = time_slots[i], time_slots[j]
            if a[1] == b[1] and a[2] < b[3] and b[2] < a[3]:
                warnings.append(
                    f"تداخل زمانی احتمالی بین {a[0]} و {b[0]} در روز {a[1]}.")

    if total_units > max_units:
        errors.append(f"مجموع واحد ({total_units}) از سقف مجاز ({max_units}) بیشتر است. {max_reason}")
    if total_units < 12:
        errors.append(f"مجموع واحد ({total_units}) از کف مجاز (۱۲) کمتر است.")

    return {
        "total_units": total_units,
        "max_units": max_units,
        "errors": errors,
        "warnings": warnings,
        "valid": len(errors) == 0,
    }


def _course_day_hint(db: Session, student: Student, code: str, term: str):
    """روز/ساعت پیشنهادی درس (پایلوت: از چارت/ارائه‌های قبلی)."""
    e = db.query(Enrollment).filter(
        Enrollment.student_id == student.id, Enrollment.course_code == code).first()
    return e.class_day if e else None


def _course_time_hint(db: Session, student: Student, code: str, term: str):
    e = db.query(Enrollment).filter(
        Enrollment.student_id == student.id, Enrollment.course_code == code).first()
    return (e.start_time, e.end_time) if e else (None, None)


def save_scenario(db: Session, student: Student, target_term: str,
                  name: str, course_codes: list[str], ip: str = None) -> dict:
    """ساخت سناریوی انتخاب واحد (STU-CRS-10) با ثبت ممیزی."""
    validation = validate_scenario(db, student, target_term, course_codes)
    scenario = CourseScenario(
        student_id=student.id, term=target_term, name=name,
        selected_course_codes=json.dumps(course_codes, ensure_ascii=False),
        total_units=validation["total_units"],
        validations=json.dumps(validation, ensure_ascii=False),
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    from app.services.student360_auth import write_audit_log
    write_audit_log(db, student_number=student.student_number, action="save-scenario",
                    entity="CourseScenario", entity_id=scenario.id,
                    detail=f"سناریو «{name}» با {validation['total_units']} واحد")
    return {
        "scenario_id": scenario.id,
        "validation": validation,
        "message": ("سناریو ذخیره شد. ثبت قطعی فقط پس از تأیید دانشجو در سامانه رسمی آموزش "
                    "معتبر است (STU-CRS-11)."),
    }


def list_scenarios(db: Session, student: Student) -> list[dict]:
    rows = db.query(CourseScenario).filter(
        CourseScenario.student_id == student.id
    ).order_by(CourseScenario.created_at.desc()).all()

    def _loads(v):
        try:
            return json.loads(v) if v else None
        except (TypeError, ValueError):
            return None

    return [
        {
            "id": s.id, "term": s.term, "name": s.name,
            "selected_course_codes": _loads(s.selected_course_codes) or [],
            "total_units": s.total_units,
            "validations": _loads(s.validations),
            "confirmed_officially": s.confirmed_officially,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        } for s in rows
    ]


# =====================================================================
# بررسی شرایط فارغ‌التحصیلی (بند ۸-۷)
# =====================================================================

def check_graduation(db: Session, student: Student) -> dict:
    """بررسی اولیه شرایط فارغ‌التحصیلی با هشدار «غیرقطعی» (STU-GRD-01..09)."""
    program = db.query(Program).filter(Program.id == student.program_id).first()
    if not program:
        return {"error": "برنامه تحصیلی یافت نشد."}

    curriculum = db.query(Curriculum).filter(
        Curriculum.program_id == program.id).all()
    best = _best_grades(db, student.id)
    passed = _passed_codes(best)

    # STU-GRD-02: واحدهای گذرانده در هر گروه
    group_units = defaultdict(int)
    for row in curriculum:
        if row.course_code in passed:
            group_units[row.course_nature] += row.credits

    # STU-GRD-03: دروس الزامی باقی‌مانده
    remaining_obligatory = [
        {"course_code": r.course_code, "course_title": r.course_title,
         "credits": r.credits, "suggested_term": r.suggested_term}
        for r in curriculum
        if r.course_nature in ("main-obligatory", "optional-obligatory")
        and r.course_code not in passed
    ]

    # STU-GRD-04: کسری واحد اختیاری/عمومی
    need_general = sum(r.credits for r in curriculum
                       if r.course_nature == "general")
    need_elective = sum(r.credits for r in curriculum
                        if r.course_nature == "elective")
    short_general = max(need_general - group_units.get("general", 0), 0)
    short_elective = max(need_elective - group_units.get("elective", 0), 0)

    gpas = compute_simple_gpa(db, student.id)
    gpa = gpas["overall"]

    # STU-GRD-05: کنترل معدل و سایر شروط
    gpa_ok = gpa >= (program.min_gpa_graduation or 12.0)

    # سنوات
    current_term_no = _estimate_current_term(student, passed)
    tenure_ok = current_term_no <= (program.max_allowed_terms or 8)

    # STU-GRD-06: مغایرت احتمالی تطبیق واحد — درس گذرانده خارج از چارت
    curriculum_codes = {r.course_code for r in curriculum}
    out_of_curriculum = [c for c in passed if c not in curriculum_codes]

    total_passed = group_units["main-obligatory"] + group_units["optional-obligatory"] + \
        group_units["general"] + group_units["elective"]
    total_ok = total_passed >= (program.total_units or 140)

    # نتیجه بررسی (بند ۸-۷)
    if not remaining_obligatory and total_ok and gpa_ok and \
            short_general == 0 and short_elective == 0 and not out_of_curriculum:
        result = "واجد شرایط اولیه فارغ‌التحصیلی"
        eligible = True
    elif remaining_obligatory:
        result = "دارای درس الزامی باقی‌مانده"
        eligible = False
    elif short_general or short_elective or not total_ok:
        result = "دارای کسری واحد"
        eligible = False
    elif out_of_curriculum:
        result = "دارای مغایرت در سرفصل یا تطبیق"
        eligible = False
    elif not gpa_ok or not tenure_ok:
        result = "نیازمند بررسی کارشناسی"
        eligible = False
    else:
        result = "نیازمند بررسی کارشناسی"
        eligible = False

    return {
        "student_number": student.student_number,
        "program": program.title,
        "curriculum_version": program.curriculum_version,
        "result": result,                       # نتیجه بررسی
        "eligible": eligible,
        "group_units": dict(group_units),       # STU-GRD-02
        "total_passed_units": total_passed,
        "total_required_units": program.total_units,
        "remaining_obligatory": remaining_obligatory,   # STU-GRD-03
        "short_general_units": short_general,           # STU-GRD-04
        "short_elective_units": short_elective,
        "gpa": gpa,
        "gpa_ok": gpa_ok,
        "current_term_estimate": current_term_no,
        "max_allowed_terms": program.max_allowed_terms,
        "tenure_ok": tenure_ok,
        "out_of_curriculum_courses": out_of_curriculum,  # STU-GRD-06
        "warning": "نتیجه اولیه و غیرقطعی است و باید توسط معاونت آموزش تأیید شود.",  # STU-GRD-08
        "expert_referral": not eligible,                  # STU-GRD-09
    }
