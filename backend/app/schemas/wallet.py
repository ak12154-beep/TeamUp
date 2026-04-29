import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.common import RequestModel, normalize_optional_text


class WalletBalanceOut(BaseModel):
    balance: int


class WalletGrantRequest(RequestModel):
    email: EmailStr
    amount: int = Field(gt=0)
    reason: str | None = None

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, "reason", max_length=255)


class WalletTransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tx_type: str
    amount: int
    reason: str | None
    event_id: uuid.UUID | None
    created_at: datetime


class WalletGrantRevokeRequest(RequestModel):
    reason: str | None = None

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, "reason", max_length=255)
