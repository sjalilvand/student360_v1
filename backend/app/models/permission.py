# app/models/permission.py
# Role-based menu permissions (Access Control Panel).
from sqlalchemy import Column, Integer, String, Boolean

from app.core.database import Base


class SysPermission(Base):
    __tablename__ = "sys_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(30), index=True, nullable=False)     # student|staff|professor
    menu_id = Column(String(40), index=True, nullable=False)  # e.g. "profile", "graph"
    enabled = Column(Boolean, default=True)
