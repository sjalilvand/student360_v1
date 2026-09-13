# app/services/behavioral_service.py
# Behavioral Insights & Engagement Index (Phase 2 / category 2).
# Foundation: stu_event_logs (auto-tracked since Phase 1).
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.event_log import StuEventLog

DEEP_EVENT_TYPES = {
    "ai_ask", "ai_enhanced", "ai_asked", "quiz_started", "quiz_submitted",
    "regulation_ask", "professor_asked", "scenario_created", "discrepancy_reported",
}
CORE_FEATURES = 10
TZ_OFFSET = timedelta(hours=3, minutes=30)  # Asia/Tehran (no DST since 2022)


def _to_tehran(dt):
    return (dt + TZ_OFFSET) if dt else dt
# python weekday(): 0=Monday..6=Sunday -> Persian order: Sat..Fri
PERSIAN_ORDER = (5, 6, 0, 1, 2, 3, 4)
PERSIAN_WEEKDAYS = ("دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه")


def _fetch(db: Session, student_ref: str, days: int):
    since = datetime.utcnow() - timedelta(days=days)
    return (db.query(StuEventLog)
            .filter(StuEventLog.student_ref == str(student_ref),
                    StuEventLog.occurred_at >= since)
            .all())


def engagement_index(db: Session, student_ref: str, days: int = 30) -> dict:
    days = max(7, min(int(days), 120))
    rows = _fetch(db, student_ref, days)
    total = len(rows)
    if total == 0:
        return {"student_ref": student_ref, "days": days, "score": 0, "level": "غیرفعال",
                "components": {"frequency": 0, "consistency": 0, "diversity": 0,
                               "depth": 0, "recency": 0},
                "total_events": 0, "active_days": 0, "distinct_types": 0,
                "deep_actions": 0, "last_activity": None}

    active_days = len({_to_tehran(r.occurred_at).date() for r in rows if r.occurred_at})
    distinct_types = len({r.event_type for r in rows})
    deep = sum(1 for r in rows if r.event_type in DEEP_EVENT_TYPES)
    last = max((r.occurred_at for r in rows if r.occurred_at), default=None)
    recency_days = (datetime.utcnow() - last).days if last else 999

    c_freq = min(total / (days * 5.0), 1.0) * 30
    c_cons = (active_days / float(days)) * 25
    c_div = min(distinct_types / float(CORE_FEATURES), 1.0) * 25
    c_depth = min(deep / 15.0, 1.0) * 15
    c_rec = 5 if recency_days <= 1 else (3 if recency_days <= 3 else (1 if recency_days <= 7 else 0))

    score = min(round(c_freq + c_cons + c_div + c_depth + c_rec), 100)
    level = ("بسیار فعال" if score >= 75 else
             "فعال" if score >= 50 else
             "کم‌تحرک" if score >= 25 else "غیرفعال")

    return {"student_ref": student_ref, "days": days, "score": score, "level": level,
            "components": {"frequency": round(c_freq), "consistency": round(c_cons),
                           "diversity": round(c_div), "depth": round(c_depth), "recency": c_rec},
            "total_events": total, "active_days": active_days,
            "distinct_types": distinct_types, "deep_actions": deep,
            "last_activity": last.isoformat() if last else None}


def insights(db: Session, student_ref: str, days: int = 30) -> dict:
    days = max(7, min(int(days), 120))
    rows = _fetch(db, student_ref, days)

    by_hour = Counter(_to_tehran(r.occurred_at).hour for r in rows if r.occurred_at)
    by_weekday = Counter(_to_tehran(r.occurred_at).weekday() for r in rows if r.occurred_at)
    by_type = Counter(r.event_type for r in rows)

    now = _to_tehran(datetime.utcnow())
    mid = now - timedelta(days=days / 2.0)
    recent = sum(1 for r in rows if r.occurred_at and r.occurred_at >= mid)
    older = len(rows) - recent
    trend = "up" if recent > older else ("down" if recent < older else "flat")

    day_set = {_to_tehran(r.occurred_at).date() for r in rows if r.occurred_at}
    streak, d = 0, now.date()
    if d not in day_set:
        d -= timedelta(days=1)
    while d in day_set:
        streak += 1
        d -= timedelta(days=1)

    peak_hour = by_hour.most_common(1)[0][0] if by_hour else None
    eng = engagement_index(db, student_ref, days)

    recs = []
    if eng["score"] < 25:
        recs.append("فعالیت شما در سامانه کم است؛ از «دستیار انتخاب واحد» و «کوییز هوشمند» شروع کنید.")
    if eng["total_events"] > 0 and eng["distinct_types"] < 5:
        recs.append(f"تنها از {eng['distinct_types']} قابلیت استفاده کرده‌اید؛ تقویم و هشدارها را هم فعال کنید.")
    if eng["components"]["depth"] < 8:
        recs.append("برای یادگیری عمیق‌تر، از «استاد هوشمند» و «کوییز هوشمند» بیشتر استفاده کنید.")
    if peak_hour is not None:
        recs.append(f"اوج فعالیت شما ساعت {peak_hour} است؛ یادآوری مطالعه را برای همین ساعت تنظیم کنید.")
    if trend == "down":
        recs.append("روند فعالیت شما نزولی شده؛ یک برنامه مطالعه هفتگی ببندید.")
    if streak >= 3:
        recs.append(f"🔥 {streak} روز متوالی فعال بوده‌اید! همین ریتم را حفظ کنید.")
    if not recs:
        recs.append("الگوی خوبی دارید؛ ادامه دهید!")

    return {"student_ref": student_ref, "days": days, "engagement": eng,
            "peak_hour": peak_hour,
            "by_hour": [{"hour": h, "count": by_hour.get(h, 0)} for h in range(24)],
            "by_weekday": [{"weekday": PERSIAN_WEEKDAYS[wd], "count": by_weekday.get(wd, 0)}
                           for wd in PERSIAN_ORDER],
            "top_features": [{"type": t, "count": c} for t, c in by_type.most_common(6)],
            "trend": trend, "trend_recent": recent, "trend_older": older,
            "streak_days": streak, "recommendations": recs}


def staff_ranking(db: Session, days: int = 30, limit: int = 50) -> list:
    since = datetime.utcnow() - timedelta(days=days)
    rows = (db.query(StuEventLog)
            .filter(StuEventLog.occurred_at >= since,
                    StuEventLog.student_ref.isnot(None))
            .all())
    per = defaultdict(list)
    for r in rows:
        per[r.student_ref].append(r)
    out = []
    for ref, evts in per.items():
        active_days = len({e.occurred_at.date() for e in evts if e.occurred_at})
        deep = sum(1 for e in evts if e.event_type in DEEP_EVENT_TYPES)
        last = max((e.occurred_at for e in evts if e.occurred_at), default=None)
        score = round(min(len(evts) / (days * 5.0), 1.0) * 40
                      + (active_days / float(days)) * 30
                      + min(deep / 15.0, 1.0) * 30)
        out.append({"student_ref": ref, "events": len(evts), "active_days": active_days,
                    "deep_actions": deep, "score": min(score, 100),
                    "last_activity": last.isoformat() if last else None})
    out.sort(key=lambda x: -x["score"])
    return out[: max(1, min(int(limit), 200))]
