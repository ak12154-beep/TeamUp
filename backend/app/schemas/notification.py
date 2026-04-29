import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    event_id: uuid.UUID | None = None
    title: str
    message: str
    notification_type: str | None = None
    action_payload: list[dict] | None = None
    is_read: bool
    created_at: datetime
