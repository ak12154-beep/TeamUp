"""add post game automation tables and notification metadata

Revision ID: 20260317_000009
Revises: 20260317_000008
Create Date: 2026-03-17 00:09:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260317_000009"
down_revision = "20260317_000008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("events", sa.Column("post_game_outcome", sa.String(length=40), nullable=True))
    op.add_column("events", sa.Column("post_game_processed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_events_post_game_outcome", "events", ["post_game_outcome"], unique=False)

    op.add_column("notifications", sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("notifications", sa.Column("notification_type", sa.String(length=50), nullable=True))
    op.add_column("notifications", sa.Column("action_payload", sa.JSON(), nullable=True))
    op.add_column("notifications", sa.Column("idempotency_key", sa.String(length=255), nullable=True))
    op.create_foreign_key(None, "notifications", "events", ["event_id"], ["id"])
    op.create_index("ix_notifications_event_id", "notifications", ["event_id"], unique=False)
    op.create_index("ix_notifications_notification_type", "notifications", ["notification_type"], unique=False)
    op.create_unique_constraint("uq_notifications_idempotency_key", "notifications", ["idempotency_key"])

    op.create_table(
        "event_ratings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "user_id", name="uq_event_ratings_event_user"),
    )
    op.create_index("ix_event_ratings_event_id", "event_ratings", ["event_id"], unique=False)
    op.create_index("ix_event_ratings_user_id", "event_ratings", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_event_ratings_user_id", table_name="event_ratings")
    op.drop_index("ix_event_ratings_event_id", table_name="event_ratings")
    op.drop_table("event_ratings")

    op.drop_constraint("uq_notifications_idempotency_key", "notifications", type_="unique")
    op.drop_index("ix_notifications_notification_type", table_name="notifications")
    op.drop_index("ix_notifications_event_id", table_name="notifications")
    op.drop_column("notifications", "idempotency_key")
    op.drop_column("notifications", "action_payload")
    op.drop_column("notifications", "notification_type")
    op.drop_column("notifications", "event_id")

    op.drop_index("ix_events_post_game_outcome", table_name="events")
    op.drop_column("events", "post_game_processed_at")
    op.drop_column("events", "post_game_outcome")
