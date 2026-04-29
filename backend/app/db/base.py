from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# noqa: F401 - импорт моделей нужен для автогенерации Alembic
from app.models import (  # isort:skip
    availability,
    email_verification,
    event,
    event_rating,
    notification,
    participant,
    sport,
    team,
    tournament_registration,
    tournament_registration_member,
    user,
    venue,
    venue_sport,
    wallet,
)
