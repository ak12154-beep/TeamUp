import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import RequestModel, ensure_timezone_aware, normalize_optional_text

SlotStatus = Literal["open", "booked", "blocked"]


class SlotCreate(RequestModel):
    start_at: datetime
    end_at: datetime
    status: SlotStatus = "open"
    note: str | None = None

    @field_validator("start_at")
    @classmethod
    def validate_start_at(cls, value: datetime) -> datetime:
        return ensure_timezone_aware(value, "start_at")

    @field_validator("end_at")
    @classmethod
    def validate_end_at(cls, value: datetime) -> datetime:
        return ensure_timezone_aware(value, "end_at")

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, "note", max_length=500)

    @model_validator(mode="after")
    def validate_range(self):
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be greater than start_at")
        return self


class SlotUpdate(RequestModel):
    start_at: datetime | None = None
    end_at: datetime | None = None
    status: SlotStatus | None = None
    note: str | None = None

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

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, "note", max_length=500)

    @model_validator(mode="after")
    def validate_range(self):
        if self.start_at is not None and self.end_at is not None and self.end_at <= self.start_at:
            raise ValueError("end_at must be greater than start_at")
        return self


class SlotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    venue_id: uuid.UUID
    start_at: datetime
    end_at: datetime
    status: str
    note: str | None = None
