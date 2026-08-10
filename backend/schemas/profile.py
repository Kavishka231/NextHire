from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from schemas.validation import optional_http_url, validate_profile_collection, validate_salary_range


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    avatar_url: str | None = Field(default=None, max_length=2048)
    headline: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    bio: str | None = Field(default=None, max_length=5000)
    open_to_work: bool | None = None

    phone: str | None = Field(default=None, max_length=50)
    linkedin_url: str | None = Field(default=None, max_length=2048)
    github_url: str | None = Field(default=None, max_length=2048)
    portfolio_url: str | None = Field(default=None, max_length=2048)

    desired_job_title: str | None = Field(default=None, max_length=200)
    preferred_job_type: str | None = Field(default=None, max_length=100)
    preferred_work_style: str | None = Field(default=None, max_length=100)
    preferred_locations: list[str] | None = Field(default=None, max_length=25)
    expected_salary_min: int | None = Field(default=None, gt=0, le=1_000_000_000)
    expected_salary_max: int | None = Field(default=None, gt=0, le=1_000_000_000)
    industries: list[str] | None = Field(default=None, max_length=25)
    available_from: date | None = None
    available_immediately: bool | None = None

    resume_file_name: str | None = Field(default=None, max_length=255)
    resume_url: str | None = Field(default=None, max_length=2048)
    resume_visible_to_recruiters: bool | None = None

    work_experience: list[dict[str, Any]] | None = Field(default=None, max_length=25)
    education: list[dict[str, Any]] | None = Field(default=None, max_length=25)
    skills: list[dict[str, Any]] | None = Field(default=None, max_length=25)
    certifications: list[dict[str, Any]] | None = Field(default=None, max_length=25)
    projects: list[dict[str, Any]] | None = Field(default=None, max_length=25)
    languages: list[dict[str, Any]] | None = Field(default=None, max_length=25)
    volunteer_experience: list[dict[str, Any]] | None = Field(default=None, max_length=25)
    achievements: list[dict[str, Any]] | None = Field(default=None, max_length=25)

    @field_validator("avatar_url", "linkedin_url", "github_url", "portfolio_url", "resume_url")
    @classmethod
    def valid_urls(cls, value: str | None):
        return optional_http_url(value)

    @field_validator("preferred_locations", "industries")
    @classmethod
    def valid_short_lists(cls, value: list[str] | None):
        if value is None:
            return None
        cleaned = []
        for item in value:
            item = item.strip()
            if not item or len(item) > 100:
                raise ValueError("List entries must be between 1 and 100 characters")
            cleaned.append(item)
        return cleaned

    @field_validator(
        "work_experience", "education", "skills", "certifications",
        "projects", "languages", "volunteer_experience", "achievements",
    )
    @classmethod
    def valid_json_collections(cls, value):
        return validate_profile_collection(value)

    @model_validator(mode="after")
    def valid_salary_range(self):
        validate_salary_range(self.expected_salary_min, self.expected_salary_max)
        return self


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    email: str
    full_name: str

    avatar_url: str | None = None
    headline: str | None = None
    location: str | None = None
    bio: str | None = None
    open_to_work: bool = False

    phone: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None

    desired_job_title: str | None = None
    preferred_job_type: str | None = None
    preferred_work_style: str | None = None
    preferred_locations: list[str] = Field(default_factory=list)
    expected_salary_min: int | None = None
    expected_salary_max: int | None = None
    industries: list[str] = Field(default_factory=list)
    available_from: date | None = None
    available_immediately: bool = True

    resume_file_name: str | None = None
    resume_url: str | None = None
    resume_visible_to_recruiters: bool = False

    work_experience: list[dict[str, Any]] = Field(default_factory=list)
    education: list[dict[str, Any]] = Field(default_factory=list)
    skills: list[dict[str, Any]] = Field(default_factory=list)
    certifications: list[dict[str, Any]] = Field(default_factory=list)
    projects: list[dict[str, Any]] = Field(default_factory=list)
    languages: list[dict[str, Any]] = Field(default_factory=list)
    volunteer_experience: list[dict[str, Any]] = Field(default_factory=list)
    achievements: list[dict[str, Any]] = Field(default_factory=list)

    completeness: int
    missing_items: list[str]
    created_at: datetime
    updated_at: datetime
