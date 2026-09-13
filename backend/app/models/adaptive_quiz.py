# app/models/adaptive_quiz.py
# Adaptive Quiz (Phase 2 / category 3): LLM-generated, level-adaptive.
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.core.database import Base


class StuAdaptiveQuiz(Base):
    __tablename__ = "stu_adaptive_quizzes"

    id = Column(Integer, primary_key=True, index=True)
    student_number = Column(String(50), index=True, nullable=False)
    course_code = Column(String(50), nullable=False)
    level = Column(String(20), nullable=False)   # easy | medium | hard
    source = Column(String(20), default="llm")   # llm | fallback
    questions = Column(Text, nullable=False)     # JSON [{question,options,correct_index,explanation}]
    created_at = Column(DateTime, default=datetime.utcnow)


class StuAdaptiveAttempt(Base):
    __tablename__ = "stu_adaptive_attempts"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, index=True, nullable=False)
    student_number = Column(String(50), index=True, nullable=False)
    course_code = Column(String(50), nullable=False)
    level = Column(String(20), nullable=False)
    answers = Column(Text, nullable=True)        # JSON [int,...]
    score_pct = Column(Integer, nullable=True)
    correct_count = Column(Integer, nullable=True)
    total = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
