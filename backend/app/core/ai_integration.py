# app/core/ai_integration.py  (v2)
# Zero-breakage AI upgrade for legacy rule-based services. When the LLM answer
# replaces the legacy text, is_low_confidence is synced so the UI stays coherent.
from __future__ import annotations

_installed = False
_ANSWER_KEYS = ("answer", "response", "reply", "text", "content")


def _longest_string(args, kwargs):
    best = None
    for a in args:
        if isinstance(a, str) and (best is None or len(a) > len(best)):
            best = a
    for v in kwargs.values():
        if isinstance(v, str) and (best is None or len(v) > len(best)):
            best = v
    return best


def _apply_ai(resp, ai):
    if not isinstance(resp, dict):
        return
    resp["ai_answer"] = ai["answer"]
    resp["ai_engine"] = ai["engine"]
    resp["ai_sources"] = ai["sources"]
    resp["ai_low_confidence"] = ai["low_confidence"]
    resp["ai_disclaimer"] = ai["disclaimer"]
    if ai["engine"] == "llm" and ai["answer"]:
        for k in _ANSWER_KEYS:
            if k in resp and isinstance(resp[k], str):
                resp[k] = ai["answer"]
                resp["ai_replaced"] = True
                resp["is_low_confidence"] = bool(ai["low_confidence"])
                break


def install_ai_integration():
    global _installed
    if _installed:
        return
    _installed = True
    try:
        from app.services import ai_enhancer
        from app.services import student360_regulations as reg_svc
        from app.services import student360_quiz_professor as prof_svc

        _orig_reg = reg_svc.ask_regulations

        def _wrapped_reg(db, *args, **kwargs):
            resp = _orig_reg(db, *args, **kwargs)
            try:
                q = _longest_string(args, kwargs)
                if q:
                    sn = None
                    for a in args:
                        if isinstance(a, str) and a != q:
                            sn = a
                            break
                    _apply_ai(resp, ai_enhancer.enhance(db, q, "regulations", sn))
            except Exception:
                pass
            return resp

        reg_svc.ask_regulations = _wrapped_reg

        _orig_prof = prof_svc.ask_smart_professor

        def _wrapped_prof(db, *args, **kwargs):
            resp = _orig_prof(db, *args, **kwargs)
            try:
                q = _longest_string(args, kwargs)
                if q:
                    _apply_ai(resp, ai_enhancer.enhance(db, q, "professor"))
            except Exception:
                pass
            return resp

        prof_svc.ask_smart_professor = _wrapped_prof

        print("AI integration v2 installed: regulations + professor")
    except Exception as exc:
        print(f"WARNING: AI integration skipped: {exc}")
