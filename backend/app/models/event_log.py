# app/models/event_log.py
# Event Tracking model (Phase 1 / Data Fast Track / STU-EVT)
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.core.database import Base


class StuEventLog(Base):
    """User behavior event log - foundation for Behavioral Insights (Phase 2)."""

    __tablename__ = "stu_event_logs"

    id = Column(Integer, primary_key=True, index=True)
    student_ref = Column(String(50), index=True, nullable=True)
    event_type = Column(String(50), index=True, nullable=False)
    event_name = Column(String(100), nullable=True)
    source = Column(String(20), nullable=True, default="api")  # web / api / system
    session_ref = Column(String(64), index=True, nullable=True)
    payload = Column(Text, nullable=True)  # JSON free-form
    occurred_at = Column(DateTime, index=True, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "student_ref": self.student_ref,
            "event_type": self.event_type,
            "event_name": self.event_name,
            "source": self.source,
            "session_ref": self.session_ref,
            "payload": self.payload,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
        }
