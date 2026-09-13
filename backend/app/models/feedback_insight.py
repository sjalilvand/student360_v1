# app/models/feedback_insight.py
# Feedback quality insights cache (Phase 2 / category 3).
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.core.database import Base


class StuFeedbackInsight(Base):
    __tablename__ = "stu_feedback_insights"

    id = Column(Integer, primary_key=True, index=True)
    days = Column(Integer, nullable=True)
    engine = Column(String(20), default="heuristic")  # llm | heuristic
    summary = Column(Text, nullable=True)
    payload = Column(Text, nullable=True)             # full JSON
    created_at = Column(DateTime, default=datetime.utcnow)
