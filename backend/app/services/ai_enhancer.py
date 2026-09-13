# app/services/ai_enhancer.py
# Shared AI enhancement: RAG + Guardrails + LLM, used to upgrade legacy
# rule-based services (regulations, professor) without breaking them.
from __future__ import annotations

from app.services import event_tracking_service as ets
from app.services import guardrails as gr
from app.services import llm_client as lc
from app.services import rag_service as rag


def enhance(db, question: str, domain: str = "regulations", student_ref=None, k: int = 5):
    """Returns {engine, answer, sources, low_confidence, disclaimer}.
    answer is None when LLM is unavailable (caller keeps legacy behavior)."""
    q = gr.sanitize_input(question)
    if len(q) < 3:
        return None

    contexts = rag.retrieve(db, q, k=k)
    answer, engine = None, "retrieval"
    if contexts:
        attempt = lc.llm_chat(gr.SYSTEM_PROMPT_FA, gr.build_user_prompt(q, contexts))
        if attempt:
            engine = "llm"
            answer = attempt

    sources = [{"title": c["title"], "kind": c["kind"], "score": c["score"]} for c in contexts]
    v = gr.validate_output(answer, contexts) if answer else {
        "ok": False, "low_confidence": True, "text": None}

    try:
        ets.track_event(db, event_type="ai_enhanced", event_name=domain,
                        student_ref=student_ref, source="api",
                        payload={"engine": engine, "sources": len(contexts),
                                 "low_confidence": v["low_confidence"]})
    except Exception:
        pass

    return {
        "engine": engine,
        "answer": v["text"] if engine == "llm" else None,
        "sources": sources,
        "low_confidence": v["low_confidence"],
        "disclaimer": gr.DISCLAIMER,
    }
