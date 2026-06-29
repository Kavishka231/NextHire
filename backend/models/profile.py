from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    avatar_url = Column(String, nullable=True)
    headline = Column(String, nullable=True)
    location = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    open_to_work = Column(Boolean, default=False, nullable=False)

    phone = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    github_url = Column(String, nullable=True)
    portfolio_url = Column(String, nullable=True)

    desired_job_title = Column(String, nullable=True)
    preferred_job_type = Column(String, nullable=True)
    preferred_work_style = Column(String, nullable=True)
    preferred_locations = Column(JSON, default=list, nullable=False)
    expected_salary_min = Column(Integer, nullable=True)
    expected_salary_max = Column(Integer, nullable=True)
    industries = Column(JSON, default=list, nullable=False)
    available_from = Column(Date, nullable=True)
    available_immediately = Column(Boolean, default=True, nullable=False)

    resume_file_name = Column(String, nullable=True)
    resume_url = Column(String, nullable=True)
    resume_visible_to_recruiters = Column(Boolean, default=False, nullable=False)

    work_experience = Column(JSON, default=list, nullable=False)
    education = Column(JSON, default=list, nullable=False)
    skills = Column(JSON, default=list, nullable=False)
    certifications = Column(JSON, default=list, nullable=False)
    projects = Column(JSON, default=list, nullable=False)
    languages = Column(JSON, default=list, nullable=False)
    volunteer_experience = Column(JSON, default=list, nullable=False)
    achievements = Column(JSON, default=list, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="profile")
