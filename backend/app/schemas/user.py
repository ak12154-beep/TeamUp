import re
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import PASSWORD_MIN_LENGTH, validate_password_strength
from app.schemas.common import (
    RequestModel,
    normalize_optional_text,
    normalize_text,
    validate_relative_or_http_url,
    validate_uuid_csv,
)

NICKNAME_RE = re.compile(r"^[\w .-]+$", re.UNICODE)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_name: str
    last_name: str
    birth_date: date
    email: EmailStr
    email_verified: bool
    role: str
    is_admin: bool = False
    nickname: str | None = None
    photo_url: str | None = None
    bio: str | None = None
    favorite_sports: str | None = None
    onboarding_score: int | None = None
    onboarding_level_label: str | None = None
    onboarding_summary: str | None = None
    onboarding_sport_focus: str | None = None
    onboarding_completed_at: datetime | None = None
    created_at: datetime | None = None


class UserProfileUpdate(RequestModel):
    nickname: str | None = Field(default=None, max_length=15)
    photo_url: str | None = None
    bio: str | None = None
    favorite_sports: str | None = None

    @field_validator("nickname")
    @classmethod
    def normalize_nickname(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = normalize_optional_text(value, "nickname", max_length=15)
        if cleaned and not NICKNAME_RE.fullmatch(cleaned):
            raise ValueError("nickname contains unsupported characters")
        return cleaned

    @field_validator("photo_url")
    @classmethod
    def validate_photo_url(cls, value: str | None) -> str | None:
        return validate_relative_or_http_url(value)

    @field_validator("bio")
    @classmethod
    def validate_bio(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, "bio", max_length=500)

    @field_validator("favorite_sports")
    @classmethod
    def validate_favorite_sports(cls, value: str | None) -> str | None:
        return validate_uuid_csv(value, "favorite_sports")


class AdminCreatePartnerRequest(RequestModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    birth_date: date
    email: EmailStr
    verification_code: str = Field(min_length=4, max_length=10)
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=128)

    @field_validator("first_name", "last_name")
    @classmethod
    def trim_names(cls, value: str) -> str:
        return normalize_text(value, "name", max_length=80)

    @field_validator("verification_code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)


class AdminUserRoleUpdateRequest(RequestModel):
    is_admin: bool


class UserWithBalance(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    role: str
    is_admin: bool = False
    photo_url: str | None = None
    bio: str | None = None
    balance: int = 0
    games_played: int = 0
    onboarding_score: int | None = None
    player_rating: float = 0


class LeaderboardPlayerOut(BaseModel):
    id: uuid.UUID
    first_name: str | None = None
    last_name: str | None = None
    nickname: str | None = None
    photo_url: str | None = None
    games_played: int = 0
    player_rating: float = 0
    rank: int


class UserEventSummary(BaseModel):
    id: uuid.UUID
    title: str
    start_at: datetime
    end_at: datetime
    status: str
    sport_name: str | None = None
    venue_name: str | None = None
    venue_city: str | None = None
    current_players: int = 0
    required_players: int


class UserProfileGamesOut(BaseModel):
    created_games: list[UserEventSummary]
    completed_games: list[UserEventSummary]
    cancelled_games: list[UserEventSummary]
