from datetime import date

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.security import PASSWORD_MIN_LENGTH, validate_password_strength
from app.schemas.common import RequestModel, normalize_text


class SendVerificationCodeRequest(RequestModel):
    email: EmailStr


class RegisterRequest(RequestModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    birth_date: date
    email: EmailStr
    verification_code: str = Field(min_length=4, max_length=10)
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=128)
    role: str | None = Field(default=None)

    @field_validator("first_name", "last_name")
    @classmethod
    def trim_names(cls, v: str) -> str:
        return normalize_text(v, "name", max_length=80)

    @field_validator("verification_code")
    @classmethod
    def normalize_code(cls, v: str) -> str:
        return v.strip()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)


class LoginRequest(RequestModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    authenticated: bool = True
    token_type: str = "cookie"
