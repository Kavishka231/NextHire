from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class JobApplication(Base):
    __tablename__ = "job_applications"
    __table_args__ = (
        UniqueConstraint(
            "applicant_user_id",
            "job_id",
            name="uq_job_applications_applicant_job",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    applicant_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    applicant_name = Column(String, nullable=False)
    applicant_email = Column(String, nullable=False)
    applicant_phone = Column(String, nullable=True)
    headline = Column(String, nullable=True)
    location = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    github_url = Column(String, nullable=True)
    portfolio_url = Column(String, nullable=True)
    resume_url = Column(String, nullable=True)
    cover_letter = Column(Text, nullable=True)
    extra_details = Column(Text, nullable=True)
    use_profile = Column(Boolean, default=True, nullable=False)
    status = Column(String, default="submitted", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    job = relationship("Job", back_populates="applications")
    applicant = relationship("User", back_populates="applications")
