# Student 360 — regulations assistant (STU-REG-01..08) and process guides (بند ۸-۴).
from __future__ import annotations

import json
from datetime import date

from sqlalchemy.orm import Session

from app.models.student360 import Regulation, ProcessGuide, Conversation
from app.services.student360_auth import write_audit_log

# =====================================================================
# بازیابی از منابع تأییدشده (STU-REG-02) — بازیابی کلیدواژه‌ای پایه.
# در فاز بعد می‌تواند با مدل زبانی/جست‌وجوی معنایی تقویت شود، اما پاسخ
# همیشه فقط از اسناد تأییدشده و با استناد ساخته می‌شود (STU-REG-03).
# =====================================================================

STOP_WORDS = {
    "از", "به", "با", "در", "که", "را", "و", "برای", "است", "آیا",
    "می", "شود", "چه", "چگونه", "کدام", "من", "من", "تا", "هم", "این", "آن",
    "درس", "دانشجو", "دانشجوی", "میخواهم", "می‌خواهم", "درباره", "چند", "حداکثر",
    "حداقل", "شده", "بودن", "کردن", "باشد", "شود", "هست",
}


def _tokenize(question: str) -> list[str]:
    import re
    words = re.findall(r"[\w\u0600-\u06FF]+", question or "")
    return [w for w in words if w not in STOP_WORDS and len(w) > 2]


def _is_active(reg: Regulation, today: date) -> bool:
    """آیین‌نامه منقضی یا لغوشده نباید در پاسخ‌گویی استفاده شود (قاعده ۹-۶)."""
    if not reg.is_active:
        return False
    if reg.valid_from and reg.valid_from > today:
        return False
    if reg.valid_to and reg.valid_to < today:
        return False
    return True


def _matches(token: str, haystack: str) -> bool:
    """تطبیق کامل یا تطبیق ریشه‌ای ساده برای صرف فارسی (مشروط/مشروطی و ...)."""
    if token in haystack:
        return True
    if len(token) >= 5 and token[:4] in haystack:
        return True
    return False


def search_regulations(db: Session, question: str, limit: int = 3) -> list[dict]:
    """بازیابی مواد مرتبط با استناد کامل (STU-REG-02 و STU-REG-03)."""
    today = date.today()
    tokens = _tokenize(question)
    active = [r for r in db.query(Regulation).all() if _is_active(r, today)]

    scored = []
    for reg in active:
        haystack = f"{reg.title} {reg.content} {reg.keywords or ''} {reg.article or ''}"
        score = sum(1 for t in tokens if _matches(t, haystack))
        if score > 0:
            scored.append((score, reg))
    scored.sort(key=lambda x: x[0], reverse=True)

    return [
        {
            "source_name": reg.source_name,
            "title": reg.title,
            "article": reg.article,
            "clause": reg.clause,
            "content": reg.content,
            "valid_from": reg.valid_from.isoformat() if reg.valid_from else None,
            "valid_to": reg.valid_to.isoformat() if reg.valid_to else None,
            "doc_type": reg.doc_type,
            "score": score,
        }
        for score, reg in scored[:limit]
    ]


def ask_regulations(db: Session, student_id: int, student_number: str, question: str, ip: str = None) -> dict:
    """دستیار آیین‌نامه‌ای: پاسخ مبتنی بر منبع با استناد، اطمینان و ارجاع."""
    refs = search_regulations(db, question)
    top_score = refs[0]["score"] if refs else 0
    # STU-REG-05 — ارجاع به کارشناس در نبود پاسخ معتبر یا تطبیق ضعیف
    weak_match = top_score < 2

    if not refs or weak_match:
        answer = ("پاسخ معتبری در منابع تأییدشده یافت نشد. لطفاً موضوع را با کارشناس "
                  "آموزش گروه خود در میان بگذارید.")
        confidence = 0.0 if not refs else 0.4
        low = True
        refs = [] if weak_match else refs
    else:
        top = refs[0]
        # STU-REG-04 — مشخص کردن پاسخ کم‌اطمینان
        if len(refs) == 1:
            confidence = 0.55
            low = True
        else:
            confidence = min(0.95, 0.6 + 0.1 * top["score"])
            low = False

        parts = []
        for ref in refs:
            clause = f" — تبصره {ref['clause']}" if ref["clause"] else ""
            parts.append(
                f"«{ref['content']}» "
                f"(منبع: {ref['source_name']}، {ref['title']}، ماده {ref['article']}{clause}، "
                f"معتبر از {ref['valid_from']} تا {ref['valid_to'] or 'اکنون'})"
            )
        answer = "\n\n".join(parts)

    conv = Conversation(
        student_id=student_id,
        assistant_type="regulations",
        question=question,
        answer=answer,
        source_refs=json.dumps(refs, ensure_ascii=False),
        confidence=confidence,
        is_low_confidence=low,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    write_audit_log(db, student_number=student_number, action="regulation-ask",
                    entity="Conversation", entity_id=conv.id,
                    detail="پرسش از دستیار آیین‌نامه‌ای")

    # STU-REG-08 — پاسخ به‌عنوان تصمیم قطعی نمایش داده نمی‌شود
    return {
        "conversation_id": conv.id,
        "answer": answer,
        "sources": refs,
        "confidence": confidence,
        "is_low_confidence": low,
        "requires_expert_referral": (not refs) or weak_match,
        "disclaimer": "این پاسخ صرفاً استناد به مقررات است و به‌منزله مجوز یا تصمیم قطعی آموزشی نیست.",
    }


def set_conversation_feedback(db: Session, student_number: str,
                              conversation_id: int, feedback: str) -> dict:
    """STU-REG-06 — ثبت مفید/غیرمفید بودن پاسخ."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        return {"ok": False, "reason": "گفتگو یافت نشد."}
    if feedback not in ("helpful", "not-helpful"):
        return {"ok": False, "reason": "بازخورد نامعتبر است."}
    conv.feedback = feedback
    db.commit()
    write_audit_log(db, student_number=student_number, action="conversation-feedback",
                    entity="Conversation", entity_id=conversation_id, detail=feedback)
    return {"ok": True}


def list_conversations(db: Session, student_id: int, assistant_type: str = None) -> list[dict]:
    q = db.query(Conversation).filter(Conversation.student_id == student_id)
    if assistant_type:
        q = q.filter(Conversation.assistant_type == assistant_type)
    rows = q.order_by(Conversation.created_at.desc()).limit(100).all()
    return [
        {
            "id": c.id, "assistant_type": c.assistant_type, "course_code": c.course_code,
            "question": c.question, "answer": c.answer,
            "confidence": c.confidence, "is_low_confidence": c.is_low_confidence,
            "feedback": c.feedback,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        } for c in rows
    ]


# =====================================================================
# راهنمای فرایندهای اداری (بند ۸-۴)
# =====================================================================

def list_process_guides(db: Session, category: str = None) -> list[dict]:
    q = db.query(ProcessGuide).filter(ProcessGuide.is_active == True)  # noqa: E712
    if category:
        q = q.filter(ProcessGuide.category == category)
    guides = q.all()

    def _loads(v):
        try:
            return json.loads(v) if v else []
        except (TypeError, ValueError):
            return []

    return [
        {
            "slug": g.slug, "title": g.title, "category": g.category,
            "conditions": g.conditions,
            "required_documents": _loads(g.required_documents),
            "steps": _loads(g.steps),
            "responsible_unit": g.responsible_unit,
            "deadline": g.deadline,
            "system_url": g.system_url,
            "processing_time": g.processing_time,
            "related_rules": g.related_rules,
        } for g in guides
    ]


def get_process_guide(db: Session, slug: str) -> Optional[dict]:
    guides = list_process_guides(db)
    for g in guides:
        if g["slug"] == slug:
            return g
    return None
