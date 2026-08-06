from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


def _validate_password_length(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters")
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    account_type: str = "candidate"
    company_name: str | None = None
    company_website: str | None = None
    company_description: str | None = None

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


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


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
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_length(v)
