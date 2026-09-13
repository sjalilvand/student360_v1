# Student 360 — calendar & reminders (بند ۸-۸) and rule-based early warnings (بند ۸-۹).
from __future__ import annotations

import json
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.student360 import (
    CalendarEvent, NotificationChannel, Alert, CounselingRequest,
    Student, Grade, Enrollment, AcademicStatus, Program, Curriculum,
)
from app.services.student360_academic import compute_simple_gpa, _best_grades, _passed_codes
from app.services.student360_auth import write_audit_log


# =====================================================================
# تقویم و یادآوری (بند ۸-۸)
# =====================================================================

EVENT_TYPES = {
    "course-selection-start", "course-selection-end", "add-drop",
    "emergency-drop", "exams", "tuition-payment", "guest-request",
    "grade-appeal", "supervisor-selection", "thesis-defense",
}


def get_calendar(db: Session, term: str = None) -> list[dict]:
    q = db.query(CalendarEvent)
    if term:
        q = q.filter(CalendarEvent.term == term)
    return [
        {
            "id": ev.id, "term": ev.term, "event_type": ev.event_type,
            "title": ev.title, "date": ev.event_date.isoformat(),
            "description": ev.description,
        } for ev in q.order_by(CalendarEvent.event_date).all()
    ]


def get_upcoming_reminders(db: Session, student: Student) -> list[dict]:
    """رویدادهای در آستانه مهلت (بر اساس offset یادآوری)."""
    today = date.today()
    events = db.query(CalendarEvent).filter(
        CalendarEvent.event_date >= today).order_by(CalendarEvent.event_date).all()
    reminders = []
    for ev in events:
        days_left = (ev.event_date - today).days
        if days_left <= (ev.reminder_offset_days or 3):
            reminders.append({
                "id": ev.id, "title": ev.title, "event_type": ev.event_type,
                "date": ev.event_date.isoformat(), "days_left": days_left,
            })
    return reminders


def get_notification_channels(db: Session, student: Student) -> dict:
    row = db.query(NotificationChannel).filter(
        NotificationChannel.student_id == student.id).first()
    if not row:
        row = NotificationChannel(student_id=student.id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return {
        "in_app": row.in_app, "sms": row.sms,
        "email": row.email, "mobile_push": row.mobile_push,
    }


def update_notification_channels(db: Session, student: Student, data: dict) -> dict:
    """دانشجو کانال اطلاع‌رسانی را تنظیم می‌کند (بند ۸-۸)."""
    row = db.query(NotificationChannel).filter(
        NotificationChannel.student_id == student.id).first()
    if not row:
        row = NotificationChannel(student_id=student.id)
        db.add(row)
    for f in ("in_app", "sms", "email", "mobile_push"):
        if f in data and data[f] is not None:
            setattr(row, f, bool(data[f]))
    db.commit()
    return get_notification_channels(db, student)


# =====================================================================
# هشدار زودهنگام پایه (بند ۸-۹) — مبتنی بر قواعد مشخص
# =====================================================================

RULES = {
    "GPA-DROP": {
        "type": "gpa-drop", "severity": "warning",
        "reason": "افت معدل نسبت به نیمسال قبل",
        "action": "با مشاور آموزشی درباره برنامه مطالعه خود مشورت کنید.",
    },
    "LOW-GRADES": {
        "type": "low-grades", "severity": "warning",
        "reason": "نمره پایین در چند ارزیابی متوالی",
        "action": "دروس نمره‌نگرفته را مرور و با استاد درس هماهنگ کنید.",
    },
    "PROBATION": {
        "type": "probation", "severity": "critical",
        "reason": "وضعیت مشروطی در نیمسال جاری",
        "action": "برنامه اصلاح معدل تهیه و با کارشناس آموزش گفت‌وگو کنید.",
    },
    "TENURE": {
        "type": "tenure-risk", "severity": "critical",
        "reason": "نزدیک‌شدن به محدودیت سنوات",
        "action": "برنامه اخذ واحدهای باقی‌مانده را با آموزش هماهنگ کنید.",
    },
    "LMS-INACTIVE": {
        "type": "lms-inactive", "severity": "warning",
        "reason": "کاهش محسوس فعالیت در سامانه یادگیری (LMS)",
        "action": "ورود منظم به سامانه یادگیری و انجام تکالیف را از سر بگیرید.",
    },
    "GRAD-SHORTAGE": {
        "type": "graduation-shortage", "severity": "info",
        "reason": "احتمال کسری واحد برای فارغ‌التحصیلی",
        "action": "گزارش کسری واحدها را در بخش فارغ‌التحصیلی ببینید.",
    },
}


def _grade_history(db: Session, student_id: int) -> list[dict]:
    grades = db.query(Grade).filter(
        Grade.student_id == student_id, Grade.grade.isnot(None)).all()
    by_term: dict[str, list[Grade]] = {}
    for g in grades:
        by_term.setdefault(g.term, []).append(g)
    out = []
    for term in sorted(by_term.keys()):
        items = by_term[term]
        pts = sum((g.grade or 0) * g.credits for g in items)
        units = sum(g.credits for g in items)
        out.append({"term": term, "gpa": round(pts / units, 2) if units else 0.0})
    return out


def _lms_activity_hint(db: Session, student: Student) -> int:
    """فعالیت LMS (پایلوت: برگرداندن ۱=فعال). در استقرار واقعی از داده LMS پر می‌شود."""
    return 1


def evaluate_alert_rules(db: Session, student: Student) -> list[Alert]:
    """تولید هشدار مبتنی بر قواعد؛ هر هشدار دارای دلیل، شدت و اقدام پیشنهادی است."""
    generated: list[Alert] = []
    history = _grade_history(db, student.id)

    # قاعده ۱: افت معدل نسبت به نیمسال قبل
    if len(history) >= 2:
        prev, last = history[-2], history[-1]
        if last["gpa"] < prev["gpa"] - 1.0:
            generated.append(Alert(
                student_id=student.id, rule_code="GPA-DROP",
                alert_type=RULES["GPA-DROP"]["type"],
                severity=RULES["GPA-DROP"]["severity"],
                reason=(f"معدل نیمسال {last['term']} ({last['gpa']}) بیش از یک واحد "
                        f"کمتر از نیمسال {prev['term']} ({prev['gpa']}) است."),
                recommended_action=RULES["GPA-DROP"]["action"],
                term=last["term"],
            ))

    # قاعده ۲: نمره پایین در چند ارزیابی متوالی (مبتنی بر کارنامه)
    low_recent = [g for g in db.query(Grade).filter(
        Grade.student_id == student.id, Grade.grade.isnot(None))
        .order_by(Grade.term.desc()).limit(4).all() if (g.grade or 0) < 12]
    if len(low_recent) >= 3:
        generated.append(Alert(
            student_id=student.id, rule_code="LOW-GRADES",
            alert_type=RULES["LOW-GRADES"]["type"],
            severity=RULES["LOW-GRADES"]["severity"],
            reason=f"{len(low_recent)} نمره کمتر از ۱۲ در آخرین ارزیابی‌ها ثبت شده است.",
            recommended_action=RULES["LOW-GRADES"]["action"],
        ))

    # قاعده ۳: مشروطی
    status = (db.query(AcademicStatus)
              .filter(AcademicStatus.student_id == student.id)
              .order_by(AcademicStatus.term.desc()).first())
    if status and status.status == "probation":
        generated.append(Alert(
            student_id=student.id, rule_code="PROBATION",
            alert_type=RULES["PROBATION"]["type"],
            severity=RULES["PROBATION"]["severity"],
            reason=status.detail or "وضعیت تحصیلی شما در نیمسال اخیر مشروط است.",
            recommended_action=RULES["PROBATION"]["action"],
            visible_to_student=True,
        ))

    # قاعده ۴: سنوات
    program = db.query(Program).filter(Program.id == student.program_id).first()
    if program:
        from app.services.student360_academic import _estimate_current_term
        passed = _passed_codes(_best_grades(db, student.id))
        term_no = _estimate_current_term(student, passed)
        if term_no >= (program.max_allowed_terms or 8) - 1:
            generated.append(Alert(
                student_id=student.id, rule_code="TENURE",
                alert_type=RULES["TENURE"]["type"],
                severity=RULES["TENURE"]["severity"],
                reason=(f"شما در ترم تقریبی {term_no} از حداکثر "
                        f"{program.max_allowed_terms} نیمسال مجاز هستید."),
                recommended_action=RULES["TENURE"]["action"],
            ))

    # قاعده ۵: عدم ورود/فعالیت LMS (پایلوت: داده نمونه)
    if _lms_activity_hint(db, student) == 0:
        generated.append(Alert(
            student_id=student.id, rule_code="LMS-INACTIVE",
            alert_type=RULES["LMS-INACTIVE"]["type"],
            severity=RULES["LMS-INACTIVE"]["severity"],
            reason="هیچ فعالیتی در ۱۴ روز گذشته در سامانه یادگیری ثبت نشده است.",
            recommended_action=RULES["LMS-INACTIVE"]["action"],
        ))

    # جلوگیری از تکرار هشدار بازِ همان قاعده
    created = []
    for alert in generated:
        exists = db.query(Alert).filter(
            Alert.student_id == student.id,
            Alert.rule_code == alert.rule_code,
            Alert.status == "open").first()
        if not exists:
            db.add(alert)
            created.append(alert)
    if created:
        db.commit()
    return created


def get_student_alerts(db: Session, student: Student) -> list[dict]:
    """فقط هشدارهای قابل نمایش به خود دانشجو (هشدار حساس برای افراد مجاز)."""
    evaluate_alert_rules(db, student)  # تولید هشدارهای جدید در صورت لزوم
    rows = db.query(Alert).filter(
        Alert.student_id == student.id,
        Alert.visible_to_student == True,  # noqa: E712
    ).order_by(Alert.created_at.desc()).all()
    return [_alert_to_dict(a) for a in rows]


def _alert_to_dict(a: Alert) -> dict:
    return {
        "id": a.id, "rule_code": a.rule_code, "alert_type": a.alert_type,
        "severity": a.severity, "reason": a.reason,
        "recommended_action": a.recommended_action,
        "status": a.status, "term": a.term,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "note": "این هشدار برای حمایت آموزشی صادر شده و هیچ تصمیم تنبیهی خودکاری در پی ندارد.",
    }


def request_counseling(db: Session, student: Student, alert_id: int,
                       message: str, ip: str = None) -> dict:
    """امکان درخواست مشاوره از بخش هشدارها (بند ۸-۹)."""
    alert = db.query(Alert).filter(
        Alert.id == alert_id, Alert.student_id == student.id).first()
    if not alert:
        return {"ok": False, "reason": "هشدار یافت نشد."}
    req = CounselingRequest(student_id=student.id, alert_id=alert.id, message=message)
    alert.status = "counseling-requested"
    db.add(req)
    db.commit()
    db.refresh(req)
    write_audit_log(db, student_number=student.student_number,
                    action="request-counseling", entity="CounselingRequest",
                    entity_id=req.id, detail=f"درخواست مشاوره برای هشدار {alert.rule_code}",
                    ip_address=ip)
    return {"ok": True, "request_id": req.id}
