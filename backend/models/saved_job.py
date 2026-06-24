from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.app.database import Base


class SavedJob(Base):
    __tablename__ = "saved_jobs"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    job = relationship("Job")