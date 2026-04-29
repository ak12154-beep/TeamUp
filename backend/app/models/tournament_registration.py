import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class TournamentRegistration(Base):
    __tablename__ = "tournament_registrations"
    __table_args__ = (
        UniqueConstraint("event_id", "captain_user_id", name="uq_tournament_event_captain"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False, index=True)
    captain_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    team_name: Mapped[str] = mapped_column(String(255), nullable=False)
    captain_first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    captain_last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    captain_phone: Mapped[str] = mapped_column(String(40), nullable=False)
    team_slogan: Mapped[str | None] = mapped_column(String(280), nullable=True)
    players_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="paid", server_default="paid")
    payment_tx_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wallet_transactions.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    event = relationship("Event", back_populates="tournament_registrations")
    members = relationship(
        "TournamentRegistrationMember",
        back_populates="registration",
        cascade="all, delete-orphan",
    )
