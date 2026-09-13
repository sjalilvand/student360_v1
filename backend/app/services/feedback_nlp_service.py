# app/services/feedback_nlp_service.py
# Feedback quality analytics (Phase 2 / category 3 completion).
# Collects dissatisfaction signals (thumbs-down, low-confidence asks),
# categorizes them, and runs LLM pattern analysis (validated JSON +
# deterministic heuristic fallback). Results cached in stu_feedback_insights.
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy import inspect as sa_inspect, text
from sqlalchemy.orm import Session

from app.models.event_log import StuEventLog
from app.models.feedback_insight import StuFeedbackInsight
from app.services import event_tracking_service as ets
from app.services import guardrails as gr

COMPLAINT_CATEGORIES = [
    ("منبع و ارجاع", ("منبع", "ارجاع", "مرجع", "مستند", "استناد")),
    ("آیین‌نامه و مقررات", ("آیین نامه", "آیین‌نامه", "مقررات", "بخشنامه", "ماده")),
    ("فرایند اداری", ("فرایند", "مراحل", "اداری", "فرم", "ثبت نام", "ثبت‌نام", "درخواست")),
    ("پاسخ نامرتبط", ("مرتبط نیست", "بی ربط", "نامربوط", "سوال من را", "پاسخ نداد")),
    ("خطا و کیفیت", ("خطا", "اشتباه", "غلط", "قدیمی", "منقضی", "درست نیست")),
]
DEFAULT_CATEGORY = "سایر"


def _pick(cols, candidates):
    for c in candidates:
        if c in cols:
            return c
    lcmap = {c.lower(): c for c in cols}
    for cand in candidates:
        for low, orig in lcmap.items():
            if cand in low:
                return orig
    return None


def _norm_feedback(v):
    s = str(v or "").strip().lower()
    if s in ("helpful", "1", "true", "up", "yes", "positive"):
        return "helpful"
    if s in ("not-helpful", "not_helpful", "0", "false", "down", "no", "negative"):
        return "not_helpful"
    return None


def _categorize_complaint(question: str) -> str:
    t = gr.sanitize_input(question or "", max_len=300).lower()
    for name, kws in COMPLAINT_CATEGORIES:
        if any(kw in t for kw in kws):
            return name
    return DEFAULT_CATEGORY


def _satisfaction_rate(helpful: int, not_helpful: int):
    tot = helpful + not_helpful
    return round(helpful * 100.0 / tot) if tot else None


def _parse_insight(raw: str):
    """Validate LLM JSON -> {themes, recommendations, summary}; None if bad."""
    if not raw:
        return None
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except Exception:
        return None
    themes = obj.get("themes") or []
    recs = obj.get("recommendations") or []
    clean = []
    for t in themes[:6]:
        if isinstance(t, dict) and str(t.get("theme", "")).strip():
            clean.append({"theme": str(t["theme"]).strip()[:120],
                          "count": int(t.get("count") or 0),
                          "example": str(t.get("example") or "").strip()[:160]})
    recs = [str(r).strip()[:220] for r in recs if str(r).strip()][:6]
    if not clean and not recs:
        return None
    return {"themes": clean, "recommendations": recs,
            "summary": str(obj.get("summary") or "").strip()[:400]}


def collect(db: Session, days: int = 30) -> dict:
    days = max(7, min(int(days), 180))
    since = datetime.utcnow() - timedelta(days=days)
    out = {"days": days, "total_conversations": 0, "with_feedback": 0,
           "helpful": 0, "not_helpful": 0, "satisfaction_pct": None,
           "low_confidence": 0, "disliked": [], "low_conf_questions": [],
           "categories": {}}

    cols = [c["name"] for c in sa_inspect(db.bind).get_columns("stu_conversations")] or []
    q_c = _pick(cols, ("question", "query", "user_message", "message"))
    fb_c = _pick(cols, ("feedback", "rating", "is_helpful", "user_feedback"))
    conf_c = _pick(cols, ("confidence", "conf"))
    ca_c = _pick(cols, ("created_at", "created", "timestamp"))

    if cols:
        try:
            rows = db.execute(text("SELECT * FROM stu_conversations")).mappings().all()
        except Exception:
            rows = []
        for r in rows:
            ca = r.get(ca_c) if ca_c else None
            # raw SQL returns strings for datetime columns -> normalize first
            ca_dt = None
            if ca is not None:
                if isinstance(ca, datetime):
                    ca_dt = ca
                else:
                    try:
                        ca_dt = datetime.fromisoformat(str(ca).replace("Z", "+00:00"))
                    except Exception:
                        ca_dt = None
            if ca_dt and ca_dt < since:
                continue
            out["total_conversations"] += 1
            fb = _norm_feedback(r.get(fb_c)) if fb_c else None
            if fb == "helpful":
                out["helpful"] += 1
                out["with_feedback"] += 1
            elif fb == "not_helpful":
                out["not_helpful"] += 1
                out["with_feedback"] += 1
                q = str(r.get(q_c) or "").strip() if q_c else ""
                if q:
                    out["disliked"].append({"q": q[:140],
                                            "cat": _categorize_complaint(q),
                                            "at": ca_dt.isoformat() if ca_dt else None})
            if conf_c:
                cv = r.get(conf_c)
                try:
                    if cv is not None and float(cv) < 0.5:
                        out["low_confidence"] += 1
                        q = str(r.get(q_c) or "").strip() if q_c else ""
                        if q:
                            out["low_conf_questions"].append(q[:140])
                except Exception:
                    pass
    out["satisfaction_pct"] = _satisfaction_rate(out["helpful"], out["not_helpful"])
    out["disliked"] = out["disliked"][-15:]
    out["low_conf_questions"] = out["low_conf_questions"][-10:]
    out["categories"] = dict(Counter(d["cat"] for d in out["disliked"]).most_common())

    # supplementary signal from event log (ai asks flagged low-confidence)
    try:
        evs = (db.query(StuEventLog)
               .filter(StuEventLog.event_type.in_(("ai_ask", "ai_enhanced")),
                       StuEventLog.occurred_at >= since).all())
        ai_low = 0
        for e in evs:
            try:
                p = json.loads(e.payload or "{}")
                if p.get("low_confidence"):
                    ai_low += 1
            except Exception:
                pass
        out["ai_low_conf_events"] = ai_low
        out["ai_events"] = len(evs)
    except Exception:
        out["ai_low_conf_events"] = out["ai_events"] = 0
    return out


_SYSTEM = """تو تحلیلگر کیفیت محصول «دانشجو ۳۶۰» هستی.
فقط یک JSON آبجکت خالص برگردان - بدون متن اضافه، بدون ``` .
ساختار: {"themes":[{"theme":"مضمون نارضایتی","count":N,"example":"نمونه کوتاه"}],
"recommendations":["اقدام پیشنهادی محصولی"], "summary":"جمع‌بندی یک‌جمله‌ای فارسی"}
قواعد: فارسی؛ حداکثر ۵ مضمون و ۵ توصیه؛ مبتنی بر داده‌های داده‌شده؛ اگر داده کافی نیست صریح بگو."""


def llm_analyze(db: Session, days: int = 30) -> dict:
    data = collect(db, days)
    snippets = [d["q"] for d in data["disliked"]] + data["low_conf_questions"]
    snippets = [gr.sanitize_input(s, max_len=160) for s in snippets][:14]

    user = (f"نرخ رضایت: {data['satisfaction_pct']}٪ | "
            f"مجموع بازخورد: {data['with_feedback']} | 👎: {data['not_helpful']} | "
            f"پاسخ کم‌اطمینان: {data['low_confidence']} | رویداد AI کم‌اطمینان: {data.get('ai_low_conf_events', 0)}\n"
            f"دسته‌بندی قاعده‌محور نارضایتی‌ها: {json.dumps(data['categories'], ensure_ascii=False)}\n"
            f"نمونه پرسش‌های نارضایتی/کم‌اطمینان:\n" +
            ("\n".join(f"- {s}" for s in snippets) if snippets else "(داده‌ای نیست)"))

    from app.services import llm_client as lc
    raw = lc.llm_chat(_SYSTEM, user)
    parsed = _parse_insight(raw)
    engine = "llm"
    if not parsed:
        engine = "heuristic"
        themes = [{"theme": cat, "count": cnt,
                   "example": next((d["q"] for d in data["disliked"] if d["cat"] == cat), "")}
                  for cat, cnt in data["categories"].items()][:5]
        recs = []
        if data["not_helpful"] and data["satisfaction_pct"] is not None and data["satisfaction_pct"] < 70:
            recs.append("نرخ رضایت پایین است؛ کیفیت منابع RAG (تازگی و پوشش آیین‌نامه‌ها) بازبینی شود.")
        if data["low_confidence"] > 0:
            recs.append("پرسش‌های کم‌اطمینان به کارشناس ارجاع داده شوند و پاسخ‌های آن‌ها مستندسازی شود.")
        if "منبع و ارجاع" in data["categories"]:
            recs.append("ساخت ارجاع‌دهی پاسخ‌ها تقویت شود (منبع + ماده + تاریخ اعتبار).")
        if not snippets:
            recs.append("داده بازخورد کافی نیست؛ فعال‌سازی درخواست بازخورد پس از هر پاسخ بررسی شود.")
        if not recs:
            recs.append("وضعیت رضایت قابل قبول است؛ پایش دوره‌ای ادامه یابد.")
        parsed = {"themes": themes, "recommendations": recs,
                  "summary": f"تحلیل قاعده‌محور {days} روز اخیر"}

    row = StuFeedbackInsight(days=days, engine=engine,
                             summary=parsed.get("summary"),
                             payload=json.dumps({"data": {k: v for k, v in data.items() if k != "days"},
                                                 "insight": parsed}, ensure_ascii=False))
    db.add(row)
    db.commit()
    db.refresh(row)
    try:
        ets.track_event(db, event_type="feedback_analyzed", event_name=f"{days}d",
                        source="system", payload={"engine": engine,
                                                  "themes": len(parsed["themes"])})
    except Exception:
        pass
    return {"id": row.id, "days": days, "engine": engine,
            "summary": parsed["summary"], "insight": parsed,
            "stats": {k: v for k, v in data.items() if k != "days"}}


def latest(db: Session):
    row = (db.query(StuFeedbackInsight)
           .order_by(StuFeedbackInsight.created_at.desc()).first())
    if not row:
        return None
    try:
        payload = json.loads(row.payload or "{}")
    except Exception:
        payload = {}
    return {"id": row.id, "days": row.days, "engine": row.engine,
            "summary": row.summary, "insight": payload.get("insight"),
            "created_at": row.created_at.isoformat() if row.created_at else None}


