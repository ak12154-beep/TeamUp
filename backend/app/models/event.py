import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    sport_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sports.id"), nullable=False, index=True)
    venue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("venues.id"), nullable=False, index=True)
    slot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("venue_slots.id"), nullable=True, index=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    required_players: Mapped[int] = mapped_column(Integer, nullable=False)
    teams_count: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_credits_per_player: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False, default="pickup", server_default="pickup", index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    entry_fee_credits_team: Mapped[int | None] = mapped_column(Integer, nullable=True)
    registration_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    registration_closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false", index=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false", index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    post_game_outcome: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    post_game_processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    teams = relationship("Team", back_populates="event", cascade="all, delete-orphan")
    participants = relationship("EventParticipant", back_populates="event", cascade="all, delete-orphan")
    ratings = relationship("EventRating", back_populates="event", cascade="all, delete-orphan")
    tournament_registrations = relationship(
        "TournamentRegistration",
        back_populates="event",
        cascade="all, delete-orphan",
    )
