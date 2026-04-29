import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TournamentRegistrationMember(Base):
    __tablename__ = "tournament_registration_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    registration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tournament_registrations.id"),
        nullable=False,
        index=True,
    )
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    is_captain: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    registration = relationship("TournamentRegistration", back_populates="members")
