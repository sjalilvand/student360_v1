# app/services/adaptive_quiz_service.py
# Adaptive quiz: level from last attempt, LLM-generated questions from course
# content, server-side grading, deterministic cloze fallback. Never raises.
from __future__ import annotations

import json
import os
import random
import re

from sqlalchemy import inspect as sa_inspect, text
from sqlalchemy.orm import Session

from app.models.adaptive_quiz import StuAdaptiveAttempt, StuAdaptiveQuiz
from app.services import event_tracking_service as ets
from app.services import llm_client as lc
from app.services import rag_service as rag

# quiz JSON needs more headroom than chat answers
try:
    os.environ["LLM_MAX_TOKENS"] = str(max(int(os.getenv("LLM_MAX_TOKENS", "800")), 1400))
except Exception:
    pass

LEVELS = ("easy", "medium", "hard")
LEVEL_FA = {"easy": "آسان", "medium": "متوسط", "hard": "پیشرفته"}


def _level_shift(level: str, score_pct: int) -> str:
    i = LEVELS.index(level) if level in LEVELS else 1
    if score_pct >= 80:
        i = min(i + 1, 2)
    elif score_pct < 50:
        i = max(i - 1, 0)
    return LEVELS[i]


def _determine_level(db: Session, sn: str, course_code: str) -> str:
    last = (db.query(StuAdaptiveAttempt)
            .filter(StuAdaptiveAttempt.student_number == str(sn),
                    StuAdaptiveAttempt.course_code == str(course_code))
            .order_by(StuAdaptiveAttempt.created_at.desc()).first())
    if not last or not last.level:
        return "medium"
    return _level_shift(last.level, int(last.score_pct or 0))


def _cols(db: Session, table: str):
    try:
        return [c["name"] for c in sa_inspect(db.bind).get_columns(table)]
    except Exception:
        return []


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


def _content_text(db: Session, course_code: str, limit: int = 1800) -> str:
    cols = _cols(db, "stu_learning_contents")
    if not cols:
        return ""
    code_c = _pick(cols, ("course_code", "code"))
    title_c = _pick(cols, ("title", "topic", "name"))
    body_c = next((c for c in cols
                   if c not in (code_c, title_c)
                   and str(db.bind.dialect).find("sqlite") >= 0 is False) or True, None)
    # prefer long text columns
    text_cols = [c for c in cols if c not in (code_c,) and
                 any(k in c.lower() for k in ("content", "body", "text", "summary", "description"))]
    if not text_cols:
        text_cols = [c for c in cols if c not in (code_c, title_c)]
    rows = []
    try:
        if code_c:
            rows = db.execute(text(
                f"SELECT * FROM stu_learning_contents WHERE {code_c} = :cc LIMIT 10"),
                {"cc": str(course_code)}).mappings().all()
    except Exception:
        rows = []
    if not rows:
        try:
            rows = db.execute(text("SELECT * FROM stu_learning_contents LIMIT 10")).mappings().all()
        except Exception:
            return ""
    parts = []
    for r in rows:
        for tc in text_cols[:3]:
            v = r.get(tc)
            if v and len(str(v).strip()) >= 15:
                parts.append(str(v).strip())
    out = "\n".join(parts)
    return out[:limit]


def _rag_fallback_text(db: Session, course_code: str) -> str:
    try:
        ctx = rag.retrieve(db, f"محتوای درس {course_code} مطالب آموزشی", k=4)
        return "\n".join(c["snippet"] for c in ctx)[:1500]
    except Exception:
        return ""


def _cloze_questions(content: str, level: str, count: int = 3):
    sents = [s.strip() for s in re.split(r"[.!؟?\n]", content or "")
             if 25 <= len(s.strip()) <= 140]
    random.shuffle(sents)
    out = []
    for s in sents:
        words = [w for w in re.findall(r"[\w\u0600-\u06FF]{4,}", s)]
        if len(words) < 4:
            continue
        target = random.choice(words)
        q = s.replace(target, "......", 1)
        distractors = [w for w in set(words) if w != target][:3]
        while len(distractors) < 3:
            distractors.append("هیچ‌کدام")
        opts = distractors[:3] + [target]
        random.shuffle(opts)
        out.append({"question": "جای خالی را پر کنید: " + q,
                    "options": opts, "correct_index": opts.index(target),
                    "explanation": "عبارت صحیح از متن درس است."})
        if len(out) >= count:
            break
    return out


_QUIZ_SYSTEM = """تو طراح سؤال آموزشی «دانشجو ۳۶۰» هستی.
فقط یک JSON آرایه‌ای خالص برگردان - بدون هیچ متن اضافه، بدون ``` .
هر عضو آرایه: {"question": "...", "options": ["...","...","...","..."],
"correct_index": 0..3, "explanation": "حداکثر ۱۵ کلمه"}
قواعد: ۳ سؤال چهارگزینه‌ای فارسی؛ فقط بر اساس «منابع» داده‌شده؛ پاسخ درست حتماً در گزینه‌ها؛
سطح دشواری مطابق درخواست؛ options دقیقاً ۴ عضو."""


def _llm_questions(db: Session, course_code: str, level: str, content: str):
    user = (f"منابع درس {course_code}:\n{content}\n\n"
            f"سطح دشواری: {LEVEL_FA[level]}\n"
            'خروجی: فقط JSON آرایه با ۳ سؤال.')
    raw = lc.llm_chat(_QUIZ_SYSTEM, user)
    if not raw:
        return None
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if not m:
        return None
    try:
        arr = json.loads(m.group(0))
    except Exception:
        return None
    valid = []
    for q in arr:
        try:
            opts = [str(o) for o in q["options"]]
            ci = int(q["correct_index"])
            if len(opts) == 4 and 0 <= ci <= 3 and len(str(q["question"]).strip()) > 5:
                valid.append({"question": str(q["question"]).strip(),
                              "options": opts, "correct_index": ci,
                              "explanation": str(q.get("explanation", "")).strip()})
        except Exception:
            continue
    return valid or None


def generate(db: Session, sn: str, course_code: str) -> dict:
    sn, cc = str(sn), str(course_code)
    level = _determine_level(db, sn, cc)
    content = _content_text(db, cc) or _rag_fallback_text(db, cc)
    questions = _llm_questions(db, cc, level, content) if content else None
    source = "llm"
    if not questions:
        questions = _cloze_questions(content or cc, level)
        source = "fallback"
    if not questions:
        questions = [{"question": f"سؤالی از درس {cc} در دسترس نیست - این یک سؤال آزمایشی است.",
                      "options": ["گزینه ۱", "گزینه ۲", "گزینه ۳", "گزینه ۴"],
                      "correct_index": 0, "explanation": "-"}]
        source = "fallback"

    row = StuAdaptiveQuiz(student_number=sn, course_code=cc, level=level,
                          source=source, questions=json.dumps(questions, ensure_ascii=False))
    db.add(row)
    db.commit()
    db.refresh(row)
    try:
        ets.track_event(db, event_type="aquiz_started", event_name=cc,
                        student_ref=sn, source="api",
                        payload={"level": level, "src": source, "n": len(questions)})
    except Exception:
        pass
    return {"quiz_id": row.id, "course_code": cc, "level": level,
            "level_label": LEVEL_FA[level], "source": source,
            "questions": [{"index": i, "question": q["question"], "options": q["options"]}
                          for i, q in enumerate(questions)]}


def submit(db: Session, sn: str, quiz_id: int, answers) -> dict:
    q = db.query(StuAdaptiveQuiz).filter(
        StuAdaptiveQuiz.id == int(quiz_id)).first()
    if not q:
        raise LookupError("quiz not found")
    questions = json.loads(q.questions or "[]")
    answers = list(answers or [])[: len(questions)]
    correct = 0
    feedback = []
    for i, qq in enumerate(questions):
        ans = answers[i] if i < len(answers) else None
        ok = (ans is not None and int(ans) == int(qq["correct_index"]))
        correct += 1 if ok else 0
        feedback.append({"index": i, "question": qq["question"],
                         "your_answer": (qq["options"][int(ans)] if ans is not None and 0 <= int(ans) < len(qq["options"]) else None),
                         "correct_answer": qq["options"][qq["correct_index"]],
                         "is_correct": ok, "explanation": qq.get("explanation", "")})
    total = len(questions)
    pct = round(correct * 100.0 / total) if total else 0
    next_level = _level_shift(q.level, pct)

    att = StuAdaptiveAttempt(quiz_id=q.id, student_number=str(sn),
                             course_code=q.course_code, level=q.level,
                             answers=json.dumps(answers), score_pct=pct,
                             correct_count=correct, total=total)
    db.add(att)
    db.commit()
    db.refresh(att)
    try:
        ets.track_event(db, event_type="aquiz_submitted", event_name=q.course_code,
                        student_ref=str(sn), source="api",
                        payload={"score": pct, "level": q.level, "next": next_level})
    except Exception:
        pass
    return {"attempt_id": att.id, "course_code": q.course_code,
            "level": q.level, "level_label": LEVEL_FA.get(q.level, q.level),
            "score_pct": pct, "correct_count": correct, "total": total,
            "next_level": next_level, "next_level_label": LEVEL_FA[next_level],
            "feedback": feedback}


def history(db: Session, sn: str, limit: int = 15) -> list:
    rows = (db.query(StuAdaptiveAttempt)
            .filter(StuAdaptiveAttempt.student_number == str(sn))
            .order_by(StuAdaptiveAttempt.created_at.desc())
            .limit(max(1, min(int(limit), 50))).all())
    return [{"id": r.id, "course_code": r.course_code,
             "level": LEVEL_FA.get(r.level, r.level), "score_pct": r.score_pct,
             "correct_count": r.correct_count, "total": r.total,
             "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]
