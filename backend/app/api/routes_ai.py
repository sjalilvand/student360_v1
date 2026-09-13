# app/api/routes_ai.py
# AI layer (Phase 1): RAG + Guardrails + LLM with graceful retrieval-only fallback.
from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import event_tracking_service as ets
from app.services import guardrails as gr
from app.services import llm_client as lc
from app.services import rag_service as rag

router = APIRouter()


class AskIn(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)
    domain: str = Field("regulations")  # regulations | study
    student_ref: Optional[str] = None


@router.get("/api/ai/status")
def ai_status(db: Session = Depends(get_db)):
    return {"llm": lc.llm_status(), "index": rag.ensure_index(db), "guardrails": "enabled"}


@router.post("/api/ai/index/refresh")
def ai_refresh(db: Session = Depends(get_db)):
    return rag.rebuild_index(db)


@router.post("/api/ai/ask")
def ai_ask(body: AskIn, db: Session = Depends(get_db)):
    t0 = time.time()
    q = gr.sanitize_input(body.question)
    if len(q) < 3:
        return {"engine": "none", "answer": "پرسش نامعتبر است.", "sources": [], "low_confidence": True}

    contexts = rag.retrieve(db, q, k=4)
    engine = "retrieval"
    answer = None
    if contexts:
        attempt = lc.llm_chat(gr.SYSTEM_PROMPT_FA, gr.build_user_prompt(q, contexts))
        if attempt:
            engine = "llm"
            answer = attempt

    if not answer:  # deterministic fallback: surface retrieved sources
        if contexts:
            lines = ["بر اساس منابع داخلی سامانه:"]
            for i, c in enumerate(contexts, 1):
                lines.append(f"{i}) {c['title']} — {c['snippet'][:220]}")
            answer = "\n".join(lines)
        else:
            answer = "منبع مرتبطی در پایگاه دانش یافت نشد؛ لطفاً به کارشناس آموزش مراجعه کنید."

    v = gr.validate_output(answer, contexts)
    latency_ms = int((time.time() - t0) * 1000)
    try:
        ets.track_event(db, event_type="ai_ask", event_name=body.domain,
                        student_ref=body.student_ref, source="api",
                        payload={"engine": engine, "latency_ms": latency_ms,
                                 "sources": len(contexts), "low_confidence": v["low_confidence"]})
    except Exception:
        pass

    return {
        "engine": engine,
        "answer": v["text"],
        "low_confidence": v["low_confidence"],
        "sources": [{"title": c["title"], "kind": c["kind"], "score": c["score"]} for c in contexts],
        "latency_ms": latency_ms,
        "disclaimer": gr.DISCLAIMER,
    }
