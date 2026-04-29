import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import RequestModel, normalize_text, validate_timezone_name


class VenueCreate(RequestModel):
    name: str = Field(min_length=2, max_length=255)
    city: str = Field(max_length=100)
    address: str = Field(max_length=255)
    hourly_rate: int = Field(ge=1)
    timezone: str = "UTC"
    sport_ids: list[uuid.UUID] = []

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return normalize_text(value, "name", max_length=255)

    @field_validator("city")
    @classmethod
    def validate_city(cls, value: str) -> str:
        return normalize_text(value, "city", max_length=100)

    @field_validator("address")
    @classmethod
    def validate_address(cls, value: str) -> str:
        return normalize_text(value, "address", max_length=255)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        return validate_timezone_name(value)


class VenueUpdate(RequestModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=255)
    hourly_rate: int | None = Field(default=None, ge=1)
    timezone: str | None = None
    sport_ids: list[uuid.UUID] | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_text(value, "name", max_length=255)

    @field_validator("city")
    @classmethod
    def validate_city(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_text(value, "city", max_length=100)

    @field_validator("address")
    @classmethod
    def validate_address(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_text(value, "address", max_length=255)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_timezone_name(value)


class VenueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    partner_user_id: uuid.UUID
    partner_email: str | None = None
    name: str
    city: str
    address: str
    hourly_rate: int
    timezone: str
    sport_ids: list[uuid.UUID] = []
