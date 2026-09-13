# Student 360 — profile service (STU-PRO-01..09).
from __future__ import annotations

import json
from typing import Optional

from sqlalchemy.orm import Session

from app.models.student360 import (
    Student, Program, Curriculum, Grade, Enrollment, AcademicStatus,
    CalendarEvent, DataDiscrepancyReport,
)
from app.services.student360_auth import write_audit_log


def _term_grades(db: Session, student_id: int, term: str):
    return db.query(Grade).filter(
        Grade.student_id == student_id, Grade.term == term).all()


def compute_gpas(db: Session, student_id: int) -> dict:
    """محاسبه معدل کل و معدل هر نیمسال (STU-PRO-03)."""
    grades = db.query(Grade).filter(
        Grade.student_id == student_id, Grade.grade.isnot(None)).all()
    term_map: dict[str, list[Grade]] = {}
    for g in grades:
        term_map.setdefault(g.term, []).append(g)

    term_gpas = {}
    total_points = total_units = 0.0
    for term, items in sorted(term_map.items()):
        pts = sum((g.grade or 0) * g.credits for g in items)
        units = sum(g.credits for g in items)
        term_gpas[term] = round(pts / units, 2) if units else 0.0
        total_points += pts
        total_units += units

    overall = round(total_points / total_units, 2) if total_units else 0.0
    return {"overall_gpa": overall, "term_gpas": term_gpas}


def get_unit_summary(db: Session, student: Student) -> dict:
    """تعداد واحد اخذشده، گذرانده، مردود و باقی‌مانده (STU-PRO-04)."""
    program = db.query(Program).filter(Program.id == student.program_id).first()
    total_required = program.total_units if program else 140

    grades = db.query(Grade).filter(Grade.student_id == student.id).all()
    enrollments = db.query(Enrollment).filter(Enrollment.student_id == student.id).all()

    # بهترین نمره هر درس (در صورت تکرار درس، آخرین نمره قبولی ملاک است)
    best: dict[str, Grade] = {}
    for g in grades:
        cur = best.get(g.course_code)
        if cur is None or (g.grade or 0) > (cur.grade or 0):
            best[g.course_code] = g

    taken = sum(g.credits for g in grades if g.status != "withdrawn")
    passed = sum(g.credits for g in best.values() if g.status == "passed")
    failed_codes = {c for c, g in best.items() if g.status == "failed"}
    failed = sum(g.credits for c, g in best.items() if g.status == "failed")
    in_progress = sum(e.credits for e in enrollments if e.status == "current")

    return {
        "total_required": total_required,
        "taken": taken,
        "passed": passed,
        "failed": failed,
        "in_progress": in_progress,
        "remaining": max(total_required - passed - in_progress, 0),
        "failed_course_codes": sorted(failed_codes),
    }


def get_profile(db: Session, student: Student) -> dict:
    """پروفایل هوشمند دانشجو — نمایش تجمیعی (بند ۸-۲ و قاعده ۹-۲)."""
    program = db.query(Program).filter(Program.id == student.program_id).first()
    gpas = compute_gpas(db, student.id)

    # Data Mart enrichment: weighted GPA from v_student_gpa (best-effort)
    try:
        from sqlalchemy import text as _sa_text
        _m = db.execute(
            _sa_text(
                "SELECT weighted_gpa, avg_score, total_credits, graded_courses "
                "FROM v_student_gpa WHERE student_number = :sn"
            ),
            {"sn": student.student_number},
        ).mappings().first()
        if _m:
            gpas["mart"] = dict(_m)
    except Exception:
        pass
    units = get_unit_summary(db, student)

    current_enrollments = db.query(Enrollment).filter(
        Enrollment.student_id == student.id, Enrollment.status == "current").all()

    # هشدارها و مهلت‌های مهم (STU-PRO-06)
    from datetime import date, timedelta
    today = date.today()
    upcoming_events = db.query(CalendarEvent).filter(
        CalendarEvent.event_date >= today,
        CalendarEvent.event_date <= today + timedelta(days=30),
    ).order_by(CalendarEvent.event_date).all()
    open_alerts = None  # فقط با مجوز برای خود دانشجو در لایه API نمایش داده می‌شود

    status_rows = db.query(AcademicStatus).filter(
        AcademicStatus.student_id == student.id).order_by(AcademicStatus.term).all()

    return {
        "identity": {  # STU-PRO-01
            "student_number": student.student_number,
            "full_name": student.full_name,
            "email": student.email,
            "phone": student.phone,
            "status": student.status,
        },
        "academic": {  # STU-PRO-02
            "program": program.title if program else None,
            "level": program.level if program else None,
            "orientation": program.orientation if program else None,
            "entry_term": student.entry_term,
            "entry_year": student.entry_year,
            "academic_status": status_rows[-1].status if status_rows else "normal",
            "probation_count": status_rows[-1].probation_count if status_rows else 0,
        },
        "gpa": {  # STU-PRO-03
            "overall": gpas["overall_gpa"],
            "by_term": gpas["term_gpas"],
            "mart": gpas.get("mart"),
        },
        "units": units,        # STU-PRO-04
        "current_courses": [   # STU-PRO-05
            {
                "course_code": e.course_code, "course_title": e.course_title,
                "credits": e.credits, "day": e.class_day,
                "start_time": e.start_time, "end_time": e.end_time,
                "instructor": e.instructor_name,
            } for e in current_enrollments
        ],
        "upcoming_events": [   # STU-PRO-06
            {
                "event_type": ev.event_type, "title": ev.title,
                "date": ev.event_date.isoformat(),
            } for ev in upcoming_events
        ],
        "last_data_update": (   # STU-PRO-07
            student.last_data_sync_at.isoformat() if student.last_data_sync_at else None
        ),
        "disclaimer": (  # قاعده مهم: جایگزین سامانه رسمی نیست
            "این پروفایل نمایش تجمیعی اطلاعات است و جایگزین سامانه رسمی آموزش نیست."
        ),
    }


def get_weekly_schedule(db: Session, student: Student) -> list[dict]:
    """برنامه هفتگی (STU-PRO-05)."""
    enrollments = db.query(Enrollment).filter(
        Enrollment.student_id == student.id, Enrollment.status == "current",
        Enrollment.class_day.isnot(None)).all()
    return [
        {
            "course_code": e.course_code, "course_title": e.course_title,
            "day": e.class_day, "start_time": e.start_time,
            "end_time": e.end_time, "instructor": e.instructor_name,
        } for e in enrollments
    ]


def report_discrepancy(db: Session, student: Student, data: dict, ip: str = None) -> DataDiscrepancyReport:
    """اعلام مغایرت اطلاعات توسط دانشجو (STU-PRO-08).
    توجه: هیچ داده رسمی تغییر نمی‌کند (STU-PRO-09)."""
    report = DataDiscrepancyReport(
        student_id=student.id,
        field=data.get("field", "unknown"),
        current_value=data.get("current_value"),
        claimed_value=data.get("claimed_value"),
        description=data.get("description"),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    write_audit_log(
        db, student_number=student.student_number, action="report-discrepancy",
        entity="DataDiscrepancyReport", entity_id=report.id,
        detail=f"اعلام مغایرت در فیلد {data.get('field')}", ip_address=ip,
    )
    return report


def list_discrepancies(db: Session, student: Student) -> list[dict]:
    rows = db.query(DataDiscrepancyReport).filter(
        DataDiscrepancyReport.student_id == student.id
    ).order_by(DataDiscrepancyReport.created_at.desc()).all()
    return [
        {
            "id": r.id, "field": r.field, "current_value": r.current_value,
            "claimed_value": r.claimed_value, "description": r.description,
            "status": r.status, "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in rows
    ]


