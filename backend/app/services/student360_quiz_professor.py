# Student 360 — smart quiz (بند ۸-۱۰) and smart professor (بند ۸-۱۱).
# Pilot phase: retrieval from verified sources with templates; no secret exam content.
from __future__ import annotations

import json
import random
import re

from sqlalchemy.orm import Session

from app.models.student360 import (
    Quiz, QuizQuestion, QuizAttempt, LearningContent, Conversation,
)
from app.services.student360_auth import write_audit_log

ENABLED_COURSES = {"CS101", "CS201", "CS301"}  # فاز اول: ۳ تا ۵ درس منتخب


# =====================================================================
# کوییز هوشمند (بند ۸-۱۰)
# =====================================================================

def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"[.؟?!]\s*", text or "")
    return [p.strip() for p in parts if len(p.strip()) > 15]


def generate_quiz(db: Session, student, course_code: str,
                  difficulty: str = "medium", count: int = 3) -> dict:
    """تولید سؤال فقط از منابع تأییدشده درس (بند ۸-۱۰)."""
    if course_code not in ENABLED_COURSES:
        return {"ok": False,
                "reason": "کوییز هوشمند در فاز اول فقط برای دروس منتخب فعال است."}

    contents = db.query(LearningContent).filter(
        LearningContent.course_code == course_code,
        LearningContent.is_verified == True,  # noqa: E712
    ).all()
    if not contents:
        return {"ok": False, "reason": "منبع تأییدشده‌ای برای این درس موجود نیست."}

    questions = []
    for content in contents:
        sentences = _split_sentences(content.content)
        for sent in sentences[:1]:
            # تولید چندگزینه‌ای ساده: جای‌گذاری کلیدواژه
            words = re.findall(r"[\w\u0600-\u06FF]{3,}", sent)
            if not words:
                continue
            answer = random.choice(words)
            distractors = [w for w in words if w != answer][:3]
            while len(distractors) < 3:
                distractors.append(f"گزینه {len(distractors) + 1}")
            options = distractors[:]
            options.append(answer)
            random.shuffle(options)

            questions.append(QuizQuestion(
                question_type="multiple-choice",
                question_text=sent.replace(answer, "........", 1) + " کدام گزینه جای خالی را کامل می‌کند؟",
                options=json.dumps(options, ensure_ascii=False),
                correct_answer=answer,
                explanation=(f"بر اساس «{content.title}» ({content.section_ref}): "
                             f"{sent}"),
                source_ref=f"{content.title} — {content.section_ref}",
                difficulty=difficulty,
                topic=content.title,
            ))

    questions = questions[:count]
    if not questions:
        return {"ok": False, "reason": "امکان تولید سؤال از منابع موجود نبود."}

    quiz = Quiz(student_id=student.id, course_code=course_code,
                title=f"کوییز هوشمند {course_code}", difficulty=difficulty,
                status="active")
    db.add(quiz)
    db.flush()
    for q in questions:
        q.quiz_id = quiz.id
        db.add(q)
    db.commit()
    db.refresh(quiz)

    write_audit_log(db, student_number=student.student_number,
                    action="quiz-generate", entity="Quiz", entity_id=quiz.id,
                    detail=f"تولید {len(questions)} سؤال برای {course_code}")

    return {"ok": True, "quiz_id": quiz.id, "course_code": course_code,
            "questions": [
                {"id": q.id, "question_type": q.question_type,
                 "question_text": q.question_text,
                 "options": json.loads(q.options) if q.options else None}
                for q in quiz.questions
            ]}


def submit_quiz(db: Session, student, quiz_id: int, answers: dict) -> dict:
    """تصحیح، پاسخ تشریحی، نقاط ضعف و پیشنهاد مطالعه (بند ۸-۱۰)."""
    quiz = db.query(Quiz).filter(
        Quiz.id == quiz_id, Quiz.student_id == student.id).first()
    if not quiz:
        return {"ok": False, "reason": "کوییز یافت نشد."}

    score = max_score = 0.0
    results = []
    weak_topics: dict[str, int] = {}

    for q in quiz.questions:
        max_score += 1
        given = answers.get(str(q.id)) or answers.get(q.id)
        correct = (given or "").strip() == (q.correct_answer or "").strip()
        if correct:
            score += 1
        else:
            weak_topics[q.topic or "عمومی"] = weak_topics.get(q.topic or "عمومی", 0) + 1
        results.append({
            "question_id": q.id, "correct": correct,
            "correct_answer": q.correct_answer,
            "explanation": q.explanation,   # پاسخ تشریحی
            "source_ref": q.source_ref,
        })

    recommendations = [
        {"topic": t, "action": f"مطالعه مجدد مبحث «{t}» و حل تمرین‌های مرتبط"}
        for t in weak_topics
    ] or [{"topic": None, "action": "سطح تسلط شما مناسب است؛ به مرور ادامه دهید."}]

    attempt = QuizAttempt(
        quiz_id=quiz.id, student_id=student.id,
        answers=json.dumps(answers, ensure_ascii=False),
        score=score, max_score=max_score,
        weak_topics=json.dumps(weak_topics, ensure_ascii=False),
        study_recommendations=json.dumps(recommendations, ensure_ascii=False),
    )
    db.add(attempt)
    db.commit()

    write_audit_log(db, student_number=student.student_number,
                    action="quiz-submit", entity="QuizAttempt", entity_id=attempt.id,
                    detail=f"نتیجه {score}/{max_score}")

    return {
        "ok": True, "score": score, "max_score": max_score,
        "percent": round(score / max_score * 100, 1) if max_score else 0,
        "results": results,
        "weak_topics": list(weak_topics.keys()),
        "study_recommendations": recommendations,
    }


def get_quiz_history(db: Session, student) -> list[dict]:
    attempts = db.query(QuizAttempt).filter(
        QuizAttempt.student_id == student.id
    ).order_by(QuizAttempt.taken_at.desc()).all()

    def _loads(v):
        try:
            return json.loads(v) if v else []
        except (TypeError, ValueError):
            return []

    return [
        {
            "attempt_id": a.id, "quiz_id": a.quiz_id,
            "course_code": (db.query(Quiz).filter(Quiz.id == a.quiz_id)
                            .first().course_code if a.quiz_id else None),
            "score": a.score, "max_score": a.max_score,
            "weak_topics": _loads(a.weak_topics),
            "taken_at": a.taken_at.isoformat() if a.taken_at else None,
        } for a in attempts
    ]


# =====================================================================
# استاد هوشمند (بند ۸-۱۱)
# =====================================================================

PROFESSOR_POLICIES = (
    "من فقط بر اساس منابع تأییدشده درس پاسخ می‌دهم و از ارائه پاسخ قطعی به "
    "تکالیف ارزیابی‌شونده خودداری می‌کنم."
)


def ask_smart_professor(db: Session, student, course_code: str,
                        question: str, mode: str = "simple") -> dict:
    """پاسخ بر اساس منابع درس؛ با ارجاع به بخش منبع و اعلان عدم اطمینان."""
    if course_code not in ENABLED_COURSES:
        return {"ok": False,
                "reason": "استاد هوشمند در فاز اول فقط برای دروس منتخب فعال است."}

    contents = db.query(LearningContent).filter(
        LearningContent.course_code == course_code,
        LearningContent.is_verified == True,  # noqa: E712
    ).all()

    # بازیابی مرتبط‌ترین بخش منبع
    q_words = set(re.findall(r"[\w\u0600-\u06FF]{3,}", question or ""))
    best_content, best_score = None, 0
    for c in contents:
        text = f"{c.title} {c.content}"
        score = sum(1 for w in q_words if w in text)
        if score > best_score:
            best_content, best_score = c, score

    if not best_content:
        answer = ("در منابع تأییدشده این درس پاسخ مرتبطی پیدا نکردم. "
                  "لطفاً سؤال را دقیق‌تر بپرسید یا از استاد درس بپرسید.")
        confidence = 0.2
        low = True
    elif best_score <= 1:
        answer = (f"بر اساس «{best_content.title}»:\n{best_content.content}\n\n"
                  "اگر منظور دیگری داشتید، سؤال را دقیق‌تر بیان کنید.")
        confidence = 0.5
        low = True
    else:
        # توضیح ساده یا پیشرفته + مثال + ارجاع به بخش منبع
        if mode == "advanced":
            answer = (f"«{best_content.title}» — {best_content.section_ref}:\n"
                      f"{best_content.content}")
        else:
            answer = (f"به زبان ساده:\n{best_content.content}\n\n"
                      f"مثال و جزئیات بیشتر: {best_content.section_ref} از «{best_content.title}».")
        confidence = min(0.9, 0.5 + 0.1 * best_score)
        low = False

    # خودداری از پاسخ قطعی به تکالیف ارزیابی‌شونده (سیاست استاد)
    if re.search(r"تکلیف|تمرین نمره|پروژه نمره", question or ""):
        answer += ("\n\n" + PROFESSOR_POLICIES)
        low = True

    conv = Conversation(
        student_id=student.id, assistant_type="smart-professor",
        course_code=course_code, question=question, answer=answer,
        source_refs=json.dumps([{
            "title": best_content.title, "section": best_content.section_ref,
        }] if best_content else [], ensure_ascii=False),
        confidence=confidence, is_low_confidence=low,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    return {
        "ok": True, "conversation_id": conv.id, "answer": answer,
        "confidence": confidence, "is_low_confidence": low,
        "sources": ([{"title": best_content.title, "section": best_content.section_ref}]
                    if best_content else []),
        "policy": PROFESSOR_POLICIES,
    }


def design_exercise(db: Session, student, course_code: str, topic: str = None) -> dict:
    """طراحی تمرین با بازخورد مرحله‌ای (بند ۸-۱۱)."""
    if course_code not in ENABLED_COURSES:
        return {"ok": False, "reason": "این درس در فاز اول فعال نیست."}
    contents = db.query(LearningContent).filter(
        LearningContent.course_code == course_code).all()
    if not contents:
        return {"ok": False, "reason": "منبعی برای طراحی تمرین موجود نیست."}

    content = contents[0]
    if topic:
        for c in contents:
            if topic in c.title or topic in (c.content or ""):
                content = c
                break

    steps = [
        {"step": 1, "task": f"تعریف مطلب «{content.title}» را با کلمات خودتان بنویسید.",
         "hint": content.section_ref},
        {"step": 2, "task": "یک مثال عددی/برنامه‌ای برای این مفهوم ارائه کنید.",
         "hint": "مثال باید با تعریف شما سازگار باشد."},
        {"step": 3, "task": "پاسخ خود را با متن منبع مقایسه و اشکالات را فهرست کنید.",
         "hint": f"منبع: {content.title} — {content.section_ref}"},
    ]
    return {"ok": True, "course_code": course_code, "topic": content.title,
            "exercise": steps, "source_ref": f"{content.title} — {content.section_ref}"}
