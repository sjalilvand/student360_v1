# app/api/routes_twin.py
# Digital Twin what-if simulation API (Phase 3 kickoff).
import json
from typing import Optional

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import digital_twin_service as twin

router = APIRouter()


class TwinCourse(BaseModel):
    code: Optional[str] = None
    title: Optional[str] = None
    credits: int
    expected_grade: float


class TwinIn(BaseModel):
    courses: Optional[list[TwinCourse]] = None
    units: Optional[int] = None
    avg_grade: Optional[float] = None


@router.post("/api/twin/simulate")
def twin_simulate(body: TwinIn,
                  x_student_number: Optional[str] = Header(default=None),
                  db: Session = Depends(get_db)):
    if not x_student_number:
        return {"error": "missing X-Student-Number"}
    courses = [c.model_dump() for c in (body.courses or [])]
    return twin.simulate(db, x_student_number, courses,
                         body.units, body.avg_grade)


class ExplainIn(BaseModel):
    simulation: dict


@router.post("/api/twin/explain")
def twin_explain(body: ExplainIn,
                 x_student_number: Optional[str] = Header(default=None),
                 db: Session = Depends(get_db)):
    """LLM explains WHY the simulation moved metrics the way it did."""
    if not x_student_number:
        return {"error": "missing X-Student-Number"}

    sim = body.simulation
    if not sim or "before" not in sim:
        return {"error": "invalid simulation payload"}

    # compact, sanitized snapshot for the prompt (no PII beyond name-less fields)
    b, a, d = sim.get("before", {}), sim.get("after", {}), sim.get("deltas", {})
    scen = sim.get("scenario", {})
    user = (
        f"سناریو: {scen.get('units')} واحد، معدل ترم {scen.get('term_gpa')}\n"
        f"قبل: GPA={b.get('gpa')}، ریسک={b.get('risk_score')} ({b.get('risk_level')})، "
        f"سقف واحد={b.get('max_units')}، مشروطی={b.get('probation_count')}، "
        f"مردودی={b.get('failed_credits')}\n"
        f"بعد: GPA={a.get('gpa')}، ریسک={a.get('risk_score')} ({a.get('risk_level')})، "
        f"سقف واحد={a.get('max_units')}، مشروطی={a.get('probation_count')}، "
        f"مردودی={a.get('failed_credits')}\n"
        f"دلتاها: GPA={d.get('gpa')}، ریسک={d.get('risk')}، سقف={d.get('max_units')}\n"
        f"هشدارها: {json.dumps(sim.get('warnings') or [], ensure_ascii=False)}\n\n"
        "به فارسی ساده و در ۳-۴ جمله توضیح بده: چرا این سناریو چنین اثری گذاشت؟ "
        "اگر ریسک کم شد بگو چرا؛ اگر زیاد شد بگو چه عاملی و چه اقدامی کمک می‌کند. "
        "از اعداد داخل توضیح استفاده کن."
    )

    from app.services import guardrails as gr
    from app.services import llm_client as lc

    q = gr.sanitize_input(user, max_len=1500)
    answer = lc.llm_chat(
        "تو مشاور تحصیلی «دانشجو ۳۶۰» هستی. فقط بر اساس اعداد داده‌شده توضیح بده. "
        "فارسی روان، ۳-۴ جمله، بدون اختراع عدد جدید. پایان پاسخ: یک جمله «پیشنهاد عملی».",
        q,
    )
    if not answer:
        answer = ("تحلیل خودکار در دسترس نیست. بر اساس اعداد: "
                  f"ریسک از {b.get('risk_score')} به {a.get('risk_score')} رسید — "
                  "عمدتاً تحت تأثیر معدل ترم و وضعیت مشروطی.")

    return {"explanation": answer, "engine": "llm" if answer else "fallback",
            "disclaimer": sim.get("disclaimer", "")}
