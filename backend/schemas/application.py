from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from core.application_status import ApplicationStatus
from schemas.validation import optional_http_url


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    external_id: str = Field(min_length=1, max_length=255)
    use_profile: bool = True
    applicant_name: str = Field(default="", max_length=150)
    applicant_email: EmailStr | None = None
    applicant_phone: str = Field(default="", max_length=50)
    headline: str = Field(default="", max_length=200)
    location: str = Field(default="", max_length=200)
    linkedin_url: str = Field(default="", max_length=2048)
    github_url: str = Field(default="", max_length=2048)
    portfolio_url: str = Field(default="", max_length=2048)
    resume_url: str = Field(default="", max_length=2048)
    cover_letter: str = Field(default="", max_length=10_000)
    extra_details: str = Field(default="", max_length=5000)

    @field_validator("linkedin_url", "github_url", "portfolio_url", "resume_url")
    @classmethod
    def valid_urls(cls, value: str):
        return optional_http_url(value) or ""


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus


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
    status: ApplicationStatus
    created_at: datetime
