# app/models/skills.py
# Career skills cache (Phase 2 / category 13).
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.core.database import Base


class StuCourseSkill(Base):
    __tablename__ = "stu_course_skills"

    id = Column(Integer, primary_key=True, index=True)
    course_code = Column(String(50), index=True, nullable=False)
    skills = Column(String(500), nullable=False, default="[]")  # JSON list
    source = Column(String(20), default="keyword")              # keyword | llm
    created_at = Column(DateTime, default=datetime.utcnow)
