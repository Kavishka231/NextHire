from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Job(Base):
    """
    Stores jobs fetched from Adzuna and cached locally.
    Full implementation comes in the Job Search feature.
    """
    __tablename__ = "jobs"

    id           = Column(Integer, primary_key=True, index=True)
    external_id  = Column(String, unique=True, index=True, nullable=False)
    title        = Column(String, nullable=False)
    company      = Column(String)
    location     = Column(String)
    description  = Column(String)
    salary_min   = Column(Integer)
    salary_max   = Column(Integer)
    url          = Column(String)
    category     = Column(String)
    is_featured  = Column(Boolean, default=False, nullable=False)
    source       = Column(String, default="adzuna", nullable=False)
    posted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    employment_type = Column(String, nullable=True)
    work_style = Column(String, nullable=True)
    experience_level = Column(String, nullable=True)
    requirements = Column(Text, nullable=True)
    responsibilities = Column(Text, nullable=True)
    benefits = Column(Text, nullable=True)
    application_email = Column(String, nullable=True)
    application_url = Column(String, nullable=True)
    application_instructions = Column(Text, nullable=True)
    deadline = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    poster = relationship("User", back_populates="posted_jobs")
