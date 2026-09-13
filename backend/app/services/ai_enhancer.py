# app/services/ai_enhancer.py
# Shared AI enhancement: RAG + Guardrails + LLM, used to upgrade legacy
# rule-based services (regulations, professor) without breaking them.
from __future__ import annotations

from app.services import event_tracking_service as ets
from app.services import guardrails as gr
from app.services import llm_client as lc
from app.services import rag_service as rag


def _graph_hint(db, question):
    """If question mentions a course (title/code), attach its graph cluster."""
    try:
        from app.services import knowledge_graph_service as kg
        from sqlalchemy import text as _t
        q = (question or "").lower().replace("\u200c", " ")
        row = db.execute(_t(
            "SELECT unique_code, unique_title FROM offered_courses")).mappings().all()
        hit = None
        for r in row:
            t = str(r["unique_title"] or "").strip().lower().replace("\u200c", " ")
            c = str(r["unique_code"] or "").strip()
            toks = [w for w in t.split() if len(w) >= 4]
            _overlap = (sum(1 for w in toks if w in q) / len(toks)) if toks else 0
            if t and (t in q or (c and len(c) >= 4 and c in q)
                      or _overlap >= 0.5):
                hit = c
                break
        if not hit:
            return ""
        cl = kg.course_cluster(db, hit)
        if cl.get("error"):
            return ""
        parts = [f"[گراف درس {cl.get('title')} ({cl.get('code')})]"]
        if cl.get("direct_prereqs"):
            parts.append(f"پیش‌نیاز مستقیم: {', '.join(cl['direct_prereqs'][:5])}")
        if cl.get("all_prereqs_recursive"):
            parts.append(f"زنجیره کامل پیش‌نیاز: {len(cl['all_prereqs_recursive'])} درس")
        if cl.get("skills"):
            parts.append(f"مهارت‌ها: {', '.join(cl['skills'][:5])}")
        if cl.get("conditions"):
            parts.append(f"شرط‌ها: {'، '.join(cl['conditions'][:3])}")
        return "\n" + "\n".join(parts)
    except Exception:
        return ""



def enhance(db, question: str, domain: str = "regulations", student_ref=None, k: int = 5):
    """Returns {engine, answer, sources, low_confidence, disclaimer}.
    answer is None when LLM is unavailable (caller keeps legacy behavior)."""
    q = gr.sanitize_input(question)
    if len(q) < 3:
        return None

    contexts = rag.retrieve(db, q, k=k)
    graph_hint = _graph_hint(db, q)
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
