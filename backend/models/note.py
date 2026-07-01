from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Note(Base):
    """Full implementation comes in the Notes feature."""
    __tablename__ = "notes"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id",       ondelete="CASCADE"), nullable=False)
    saved_job_id = Column(Integer, ForeignKey("saved_jobs.id",  ondelete="CASCADE"), nullable=False)
    content      = Column(Text, nullable=False)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    user      = relationship("User",     back_populates="notes")
    saved_job = relationship("SavedJob", back_populates="notes")
