# app/models/intervention.py
# Smart Intervention (Phase 2): risk warning -> staff action loop.
# Supportive only - never an automatic punitive decision (document rule).
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.core.database import Base

STATUS_LABELS = {
    "open": "در انتظار بررسی",
    "in_progress": "در حال پیگیری",
    "reviewed": "بررسی شد",
    "closed": "بسته شد",
}


class StuIntervention(Base):
    __tablename__ = "stu_interventions"

    id = Column(Integer, primary_key=True, index=True)
    student_number = Column(String(50), index=True, nullable=False)
    student_name = Column(String(200), nullable=True)
    risk_score = Column(Integer, nullable=True)
    risk_level = Column(String(20), nullable=False)
    reasons = Column(Text, nullable=True)            # JSON list (fa)
    suggested_actions = Column(Text, nullable=True)  # JSON list (fa)
    status = Column(String(20), default="open", index=True)
    review_note = Column(Text, nullable=True)
    reviewed_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "student_number": self.student_number,
            "student_name": self.student_name,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "reasons": self.reasons,
            "suggested_actions": self.suggested_actions,
            "status": self.status,
            "status_label": STATUS_LABELS.get(self.status, self.status),
            "review_note": self.review_note,
            "reviewed_by": self.reviewed_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
        }
