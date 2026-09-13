# app/services/guardrails.py
# Prompt Guardrails: input sanitization, strict system prompt, output validation (STU-REG rules).
from __future__ import annotations

import re

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)",
    r"system\s*prompt",
    r"you\s+are\s+now",
    r"disregard\s+(all|any)",
    r"<\s*/?\s*(system|assistant|tool)\s*>",
]


def sanitize_input(text: str, max_len: int = 1000) -> str:
    t = (text or "")
    t = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", t)
    for pat in INJECTION_PATTERNS:
        t = re.sub(pat, " ", t, flags=re.IGNORECASE)
    t = re.sub(r"\s{3,}", "  ", t).strip()
    return t[:max_len]


SYSTEM_PROMPT_FA = """تو دستیار آموزشی «دانشجو ۳۶۰» هستی.
قواعد الزامی:
۱) فقط بر اساس «منابع» ارائه‌شده پاسخ بده؛ برای قواعد آموزشی از دانش بیرونی استفاده نکن.
۲) هر گزاره باید ارجاع منبع داشته باشد؛ فرمت ارجاع: [منبع: عنوان].
۳) اگر منابع کافی نیست، صریح بگو که باید به کارشناس آموزش مراجعه شود.
۴) هیچ اقدام قطعی اداری/ثبتی انجام نمی‌دهی و ادعای قطعیت نمی‌کنی؛ پاسخ همیشه «اولیه» است.
۵) داده‌های شخصی دانشجو را تکرار یا افشا نکن.
۶) پاسخ فارسی، کوتاه و ساختاریافته (حداکثر ~۲۰۰ کلمه)."""


def build_user_prompt(question: str, contexts: list) -> str:
    blocks = []
    for i, c in enumerate(contexts, 1):
        blocks.append(f"[منبع {i}: {c['title']} | نوع: {c['kind']}]\n{c['snippet']}")
    ctx = "\n\n".join(blocks) if blocks else "(منبعی یافت نشد)"
    return f"منابع:\n{ctx}\n\nپرسش دانشجو:\n{question}"


DISCLAIMER = "⚠️ این پاسخ اولیه و غیرقطعی است؛ برای اقدام رسمی به کارشناس آموزش مراجعه کنید."


def validate_output(answer: str, contexts: list) -> dict:
    ok = bool(answer and answer.strip())
    low = (answer or "").lower()
    refusal = any(x in low for x in ("نمی‌دانم", "نمی دانم", "اطلاعی ندارم"))
    low_conf = (not ok) or refusal or (len(contexts) == 0)
    text = (answer or "").strip()
    if ok and DISCLAIMER not in text and ("منبع" not in text):
        text += "\n\n" + DISCLAIMER
    if ok and low_conf and DISCLAIMER not in text:
        text += "\n\n" + DISCLAIMER
    return {"ok": ok, "low_confidence": low_conf, "text": text}
