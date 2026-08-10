from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator

from schemas.validation import optional_http_url, validate_salary_range


class AdminRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CompanyApprovalRequest(AdminRequest):
    approved: StrictBool


class AdminUserSecurityUpdate(AdminRequest):
    is_active: StrictBool | None = None
    is_verified: StrictBool | None = None
    banned_until: AwareDatetime | None = None

    @field_validator("is_active", "is_verified", mode="before")
    @classmethod
    def boolean_cannot_be_null(cls, value):
        if value is None:
            raise ValueError("Boolean security fields cannot be null")
        return value

    @model_validator(mode="after")
    def has_update(self):
        if not self.model_fields_set:
            raise ValueError("At least one security field is required")
        return self


class AdminPasswordResetRequest(AdminRequest):
    new_password: str = Field(min_length=8, max_length=128)


class AdminFeaturedJobCreate(AdminRequest):
    external_id: str | None = Field(default=None, min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=200)
    company: str = Field(default="", max_length=200)
    location: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=5000)
    salary_min: int | None = Field(default=None, gt=0, le=1_000_000_000)
    salary_max: int | None = Field(default=None, gt=0, le=1_000_000_000)
    url: str = Field(default="", max_length=2048)
    category: str = Field(default="featured", max_length=100)

    @field_validator("url")
    @classmethod
    def valid_url(cls, value: str):
        return optional_http_url(value) or ""

    @model_validator(mode="after")
    def valid_salary_range(self):
        validate_salary_range(self.salary_min, self.salary_max)
        return self


class AdminJobUpdate(AdminRequest):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    salary_min: int | None = Field(default=None, gt=0, le=1_000_000_000)
    salary_max: int | None = Field(default=None, gt=0, le=1_000_000_000)
    category: str | None = Field(default=None, max_length=100)
    is_featured: StrictBool | None = None
    is_active: StrictBool | None = None
    application_email: str | None = Field(default=None, max_length=320)
    application_url: str | None = Field(default=None, max_length=2048)
    application_instructions: str | None = Field(default=None, max_length=5000)

    @field_validator("title", "is_featured", "is_active", mode="before")
    @classmethod
    def required_values_cannot_be_null(cls, value):
        if value is None:
            raise ValueError("This job field cannot be null")
        return value

    @field_validator("application_url")
    @classmethod
    def valid_application_url(cls, value: str | None):
        return optional_http_url(value) if value is not None else None

    @model_validator(mode="after")
    def has_update(self):
        if not self.model_fields_set:
            raise ValueError("At least one job field is required")
        return self


class ProfileModerationRequest(AdminRequest):
    clear_avatar_url: StrictBool = False
    clear_headline: StrictBool = False
    clear_bio: StrictBool = False

    @model_validator(mode="after")
    def clears_content(self):
        if not any((self.clear_avatar_url, self.clear_headline, self.clear_bio)):
            raise ValueError("At least one profile field must be cleared")
        return self


AdminRole = Literal["super_admin", "moderator", "analyst"]
