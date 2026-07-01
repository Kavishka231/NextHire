from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProfileUpdate(BaseModel):
    avatar_url: str | None = None
    headline: str | None = None
    location: str | None = None
    bio: str | None = None
    open_to_work: bool | None = None

    phone: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None

    desired_job_title: str | None = None
    preferred_job_type: str | None = None
    preferred_work_style: str | None = None
    preferred_locations: list[str] | None = None
    expected_salary_min: int | None = None
    expected_salary_max: int | None = None
    industries: list[str] | None = None
    available_from: date | None = None
    available_immediately: bool | None = None

    resume_file_name: str | None = None
    resume_url: str | None = None
    resume_visible_to_recruiters: bool | None = None

    work_experience: list[dict[str, Any]] | None = None
    education: list[dict[str, Any]] | None = None
    skills: list[dict[str, Any]] | None = None
    certifications: list[dict[str, Any]] | None = None
    projects: list[dict[str, Any]] | None = None
    languages: list[dict[str, Any]] | None = None
    volunteer_experience: list[dict[str, Any]] | None = None
    achievements: list[dict[str, Any]] | None = None


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
