import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import (
    RequestModel,
    ensure_timezone_aware,
    normalize_optional_text,
    normalize_text,
)

EventStatus = Literal["active", "cancelled", "completed"]
EventType = Literal["pickup", "tournament"]


class EventCreate(RequestModel):
    sport_id: uuid.UUID
    venue_id: uuid.UUID
    slot_id: uuid.UUID | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    required_players: int = Field(ge=2)
    teams_count: int = Field(ge=2, le=4)
    duration_hours: int = Field(ge=1, le=3)
    auto_join_creator: bool = True

    @field_validator("start_at")
    @classmethod
    def validate_start_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_timezone_aware(value, "start_at")

    @field_validator("end_at")
    @classmethod
    def validate_end_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_timezone_aware(value, "end_at")

    @model_validator(mode="after")
    def validate_time_or_slot(self):
        if not self.slot_id and (not self.start_at or not self.end_at):
            raise ValueError("slot_id or start_at/end_at must be provided")
        if self.start_at and self.end_at and self.end_at <= self.start_at:
            raise ValueError("end_at must be greater than start_at")
        return self


class EventUpdate(RequestModel):
    status: EventStatus | None = None
    required_players: int | None = Field(default=None, ge=2)
    teams_count: int | None = Field(default=None, ge=2, le=4)
    registration_closed: bool | None = None


class EventJoinRequest(RequestModel):
    team_number: int | None = Field(default=None, ge=1)


class EventRatingCreate(RequestModel):
    rating: int = Field(ge=1, le=5)


class TournamentCreateRequest(RequestModel):
    title: str = Field(min_length=3, max_length=255)
    sport_id: uuid.UUID
    venue_id: uuid.UUID
    slot_id: uuid.UUID | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    teams_count: int = Field(ge=2, le=64)
    entry_fee_credits_team: int = Field(ge=1)
    registration_deadline: datetime
    description: str | None = Field(default=None, max_length=3000)
    is_featured: bool = True

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return normalize_text(value, "title", max_length=255)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, "description", max_length=3000)

    @field_validator("start_at")
    @classmethod
    def validate_start_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_timezone_aware(value, "start_at")

    @field_validator("end_at")
    @classmethod
    def validate_end_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_timezone_aware(value, "end_at")

    @field_validator("registration_deadline")
    @classmethod
    def validate_registration_deadline(cls, value: datetime) -> datetime:
        return ensure_timezone_aware(value, "registration_deadline")

    @model_validator(mode="after")
    def validate_schedule(self):
        if not self.slot_id and (not self.start_at or not self.end_at):
            raise ValueError("slot_id or start_at/end_at must be provided")
        if self.start_at and self.end_at and self.end_at <= self.start_at:
            raise ValueError("end_at must be greater than start_at")
        if self.start_at and self.registration_deadline >= self.start_at:
            raise ValueError("registration_deadline must be before start_at")
        return self


class TournamentRegistrationMemberCreate(RequestModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    is_captain: bool = False

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, value: str) -> str:
        return normalize_text(value, "first_name", max_length=80)

    @field_validator("last_name")
    @classmethod
    def validate_last_name(cls, value: str) -> str:
        return normalize_text(value, "last_name", max_length=80)


class TournamentTeamRegisterRequest(RequestModel):
    team_name: str = Field(min_length=2, max_length=255)
    team_slogan: str | None = Field(default=None, max_length=280)
    captain_first_name: str = Field(min_length=1, max_length=80)
    captain_last_name: str = Field(min_length=1, max_length=80)
    captain_phone: str = Field(min_length=5, max_length=40)
    players_count: int = Field(ge=1, le=100)
    members: list[TournamentRegistrationMemberCreate] = Field(min_length=1, max_length=100)

    @field_validator("team_name")
    @classmethod
    def validate_team_name(cls, value: str) -> str:
        return normalize_text(value, "team_name", max_length=255)

    @field_validator("team_slogan")
    @classmethod
    def validate_team_slogan(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, "team_slogan", max_length=280)

    @field_validator("captain_first_name")
    @classmethod
    def validate_captain_first_name(cls, value: str) -> str:
        return normalize_text(value, "captain_first_name", max_length=80)

    @field_validator("captain_last_name")
    @classmethod
    def validate_captain_last_name(cls, value: str) -> str:
        return normalize_text(value, "captain_last_name", max_length=80)

    @field_validator("captain_phone")
    @classmethod
    def validate_captain_phone(cls, value: str) -> str:
        return normalize_text(value, "captain_phone", max_length=40)

    @model_validator(mode="after")
    def validate_members(self):
        if self.players_count != len(self.members):
            raise ValueError("players_count must match the number of members")
        captain_count = sum(1 for member in self.members if member.is_captain)
        if captain_count != 1:
            raise ValueError("Exactly one member must be marked as captain")
        return self


class TeamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    team_number: int


class ParticipantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    team_id: uuid.UUID | None
    status: str
    first_name: str | None = None
    last_name: str | None = None
    nickname: str | None = None
    user_email: str | None = None
    user_rating: float | None = None
    onboarding_score: int | None = None


class TournamentRegistrationMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_name: str
    last_name: str
    is_captain: bool


class TournamentRegistrationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    team_name: str
    team_slogan: str | None = None
    players_count: int
    status: str
    created_at: datetime


class TournamentRegistrationAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    team_name: str
    team_slogan: str | None = None
    captain_name: str
    captain_user_id: uuid.UUID
    captain_phone: str
    players_count: int
    status: str
    payment_tx_id: uuid.UUID | None = None
    created_at: datetime
    members: list[TournamentRegistrationMemberOut] = Field(default_factory=list)


class TournamentRegistrationAdminUpdate(RequestModel):
    team_slogan: str | None = Field(default=None, max_length=280)

    @field_validator("team_slogan")
    @classmethod
    def validate_team_slogan(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, "team_slogan", max_length=280)


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    created_by_user_id: uuid.UUID
    sport_id: uuid.UUID
    venue_id: uuid.UUID
    slot_id: uuid.UUID | None
    start_at: datetime
    end_at: datetime
    required_players: int
    teams_count: int
    duration_hours: int
    cost_credits_per_player: int
    event_type: EventType = "pickup"
    description: str | None = None
    entry_fee_credits_team: int | None = None
    registration_deadline: datetime | None = None
    registration_closed: bool = False
    registration_is_closed: bool = False
    is_featured: bool = False
    rent_total: int = 0
    rent_share_per_player: int = 0
    platform_fee_per_player: int = 0
    admin_rent_total: int = 0
    admin_platform_fee_total: int = 0
    partner_rent_revenue: int = 0
    pricing_applied: bool = False
    refund_required: bool = False
    status: str
    teams: list[TeamOut] = []
    participants: list[ParticipantOut] = []
    # Дополнительно вычисляемые поля
    sport_name: str | None = None
    venue_name: str | None = None
    venue_address: str | None = None
    venue_city: str | None = None
    current_players: int = 0
    registered_teams_count: int = 0
    tournament_registrations: list[TournamentRegistrationOut] = Field(default_factory=list)
    post_game_outcome: str | None = None
