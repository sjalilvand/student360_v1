# app/services/ai_enhancer.py  (v2 - full rewrite)
# Shared AI enhancement: RAG + Graph hint + Guardrails + LLM.
# Upgrades legacy rule-based services (regulations, professor) without breaking them.
from __future__ import annotations

from app.services import event_tracking_service as ets
from app.services import guardrails as gr
from app.services import llm_client as lc
from app.services import rag_service as rag

_INVISIBLE = ("\u200b", "\u200c", "\u200e", "\u200f", "\ufeff")


def _clean_text(s):
    """Lowercase + remove ALL invisible/bidi marks (ZWNJ, ZWSP, LRM, RLM, BOM)."""
    s = (s or "").lower()
    for ch in _INVISIBLE:
        s = s.replace(ch, "")
    return " ".join(s.split())


def _graph_hint(db, question):
    """If the question mentions a course (title/code), attach its graph cluster."""
    try:
        from sqlalchemy import text as _t

        from app.services import knowledge_graph_service as kg

        q = _clean_text(question)
        rows = db.execute(_t(
            "SELECT unique_code, unique_title FROM offered_courses")).mappings().all()

        hit, best_ov = None, 0.0
        for r in rows:
            t = _clean_text(r["unique_title"])
            c = str(r["unique_code"] or "").strip()
            if not t:
                continue
            if t in q:                       # full clean title inside question: definitive
                hit, best_ov = c, 1.0
                break
            toks = [w for w in t.split() if len(w) >= 4]
            ov = (sum(1 for w in toks if w in q) / len(toks)) if toks else 0.0
            if ov > best_ov:
                hit, best_ov = c, ov
        if hit is None or best_ov < 0.5:
            return ""

        cl = kg.course_cluster(db, hit)
        if cl.get("error"):
            return ""
        parts = [f"[گراف درس {cl.get('title')} ({cl.get('code')})]"]
        if cl.get("direct_prereqs"):
            parts.append("پیش‌نیاز مستقیم: "
                         + ", ".join(str(x) for x in cl["direct_prereqs"][:5]))
        if cl.get("all_prereqs_recursive"):
            nn = len(cl["all_prereqs_recursive"])
            sample = ", ".join(str(x) for x in cl["all_prereqs_recursive"][:6])
            parts.append(f"زنجیره کامل پیش‌نیاز ({nn} درس): {sample}")
        if cl.get("skills"):
            parts.append("مهارت‌ها: " + ", ".join(str(x) for x in cl["skills"][:5]))
        if cl.get("conditions"):
            parts.append("شرط‌ها: " + "، ".join(str(x) for x in cl["conditions"][:3]))
        return "\n" + "\n".join(parts)
    except Exception:
        return ""


def enhance(db, question: str, domain: str = "regulations",
            student_ref=None, k: int = 5):
    """Returns {engine, answer, sources, low_confidence, disclaimer}.
    answer is None when LLM is unavailable (caller keeps legacy behavior)."""
    q = gr.sanitize_input(question)
    if len(q) < 3:
        return None

    contexts = rag.retrieve(db, q, k=k)
    graph_hint = _graph_hint(db, q)

    answer, engine = None, "retrieval"
    if contexts or graph_hint:
        user_prompt = gr.build_user_prompt(q, contexts)
        if graph_hint:
            user_prompt += "\n\nاطلاعات گراف دروس:\n" + graph_hint
        attempt = lc.llm_chat(gr.SYSTEM_PROMPT_FA, user_prompt)
        if attempt:
            engine = "llm"
            answer = attempt

    sources = [{"title": c["title"], "kind": c["kind"], "score": c["score"]}
               for c in contexts]
    v = gr.validate_output(answer, contexts) if answer else {
        "ok": False, "low_confidence": True, "text": None}

    try:
        ets.track_event(db, event_type="ai_enhanced", event_name=domain,
                        student_ref=student_ref, source="api",
                        payload={"engine": engine, "sources": len(contexts),
                                 "low_confidence": v["low_confidence"],
                                 "graph_hint": bool(graph_hint)})
    except Exception:
        pass

    return {
        "engine": engine,
        "answer": v["text"] if engine == "llm" else None,
        "sources": sources,
        "low_confidence": v["low_confidence"],
        "disclaimer": gr.DISCLAIMER,
    }
