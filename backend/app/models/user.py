import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false", index=True)
    nickname: Mapped[str | None] = mapped_column(String(15), nullable=True, index=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    favorite_sports: Mapped[str | None] = mapped_column(Text, nullable=True)  # id видов спорта через запятую
    onboarding_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    onboarding_level_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    onboarding_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    onboarding_sport_focus: Mapped[str | None] = mapped_column(String(120), nullable=True)
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    wallet_account = relationship("WalletAccount", back_populates="user", uselist=False)
    venues = relationship("Venue", back_populates="partner")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
