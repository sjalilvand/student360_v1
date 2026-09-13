# app/api/routes_jalali.py
# Jalali (Shamsi) event calendar + daily series (Persian analytics).
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.event_log import StuEventLog
from app.utils.jalali import (
    JALALI_MONTH_NAMES,
    fa_str,
    gregorian_to_jalali,
    jalali_month_length,
    jalali_to_gregorian,
    today_jalali,
    weekday_index_fa,
)

router = APIRouter()


@router.get("/api/events/daily-jalali")
def events_daily_jalali(days: int = Query(14, ge=1, le=120), db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(StuEventLog.occurred_at)
        .filter(StuEventLog.occurred_at >= since)
        .all()
    )
    per_day = defaultdict(int)
    for (occ,) in rows:
        if occ:
            per_day[occ.date().isoformat()] += 1
    items = []
    for day_iso in sorted(per_day):
        y, m, d = (int(x) for x in day_iso.split("-"))
        jy, jm, jd = gregorian_to_jalali(y, m, d)
        items.append({"date": day_iso, "jalali": fa_str(jy, jm, jd), "count": per_day[day_iso]})
    return {"days": days, "items": items, "total": sum(per_day.values())}


@router.get("/api/events/calendar-jalali")
def events_calendar_jalali(
    year: int = Query(0, ge=0),
    month: int = Query(0, ge=0, le=12),
    db: Session = Depends(get_db),
):
    jy_now, jm_now, jd_now = today_jalali()
    jy = year or jy_now
    jm = month or jm_now
    if jm < 1 or jm > 12:
        jm = jm_now
    gy, gm, gd = jalali_to_gregorian(jy, jm, 1)
    first = datetime(gy, gm, gd)
    length = jalali_month_length(jy, jm)
    end = first + timedelta(days=length)
    rows = (
        db.query(StuEventLog.occurred_at)
        .filter(StuEventLog.occurred_at >= first, StuEventLog.occurred_at < end)
        .all()
    )
    counts = defaultdict(int)
    for (occ,) in rows:
        if occ:
            counts[occ.date().isoformat()] += 1
    grid = []
    for d in range(1, length + 1):
        gyd, gmd, gdd = jalali_to_gregorian(jy, jm, d)
        dt = datetime(gyd, gmd, gdd)
        grid.append({
            "day": d,
            "count": counts.get(dt.date().isoformat(), 0),
            "weekday_index": weekday_index_fa(dt),
            "is_today": (jy == jy_now and jm == jm_now and d == jd_now),
        })
    return {
        "year": jy,
        "month": jm,
        "month_name": JALALI_MONTH_NAMES[jm - 1],
        "month_length": length,
        "total_events": sum(counts.values()),
        "today_jalali": fa_str(jy_now, jm_now, jd_now),
        "days": grid,
    }
