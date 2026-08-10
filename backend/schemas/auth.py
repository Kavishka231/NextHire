from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from schemas.validation import optional_http_url


def _validate_password_length(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters")
    if len(value) > 128:
        raise ValueError("Password must not exceed 128 characters")
    return value


class RegisterRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=150)
    password: str
    account_type: str = "candidate"
    company_name: str | None = Field(default=None, max_length=200)
    company_website: str | None = Field(default=None, max_length=2048)
    company_description: str | None = Field(default=None, max_length=5000)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_length(v)

    @field_validator("full_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Full name cannot be empty")
        return v.strip()

    @field_validator("account_type")
    @classmethod
    def valid_account_type(cls, v: str) -> str:
        if v not in {"candidate", "company"}:
            raise ValueError("Account type must be candidate or company")
        return v

    @field_validator("company_website")
    @classmethod
    def valid_company_website(cls, value: str | None):
        return optional_http_url(value)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("token")
    @classmethod
    def token_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Reset token is required")
        return value.strip()

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        return _validate_password_length(value)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    account_type: str = "candidate"
    company_name: str | None = None
    company_status: str = "none"
    company_verified: bool = False
    is_admin: bool = False

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_length(v)
