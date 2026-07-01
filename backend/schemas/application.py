from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class ApplicationCreate(BaseModel):
    external_id: str
    use_profile: bool = True
    applicant_name: str = ""
    applicant_email: EmailStr | None = None
    applicant_phone: str = ""
    headline: str = ""
    location: str = ""
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""
    resume_url: str = ""
    cover_letter: str = ""
    extra_details: str = ""


class ApplicationStatusUpdate(BaseModel):
    status: str


class ApplicationResponse(BaseModel):
    id: int
    job_id: int
    external_id: str
    job_title: str
    company: str
    applicant_name: str
    applicant_email: EmailStr
    applicant_phone: Optional[str] = None
    headline: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    resume_url: Optional[str] = None
    cover_letter: Optional[str] = None
    extra_details: Optional[str] = None
    use_profile: bool
    status: str
    created_at: datetime
