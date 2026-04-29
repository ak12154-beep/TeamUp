"""add tournaments and team registrations

Revision ID: 20260405_000010
Revises: 20260317_000009
Create Date: 2026-04-05 00:10:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260405_000010"
down_revision = "20260317_000009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column("event_type", sa.String(length=20), nullable=False, server_default="pickup"),
    )
    op.add_column("events", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("events", sa.Column("entry_fee_credits_team", sa.Integer(), nullable=True))
    op.add_column("events", sa.Column("registration_deadline", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "events",
        sa.Column("registration_closed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "events",
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_events_event_type", "events", ["event_type"], unique=False)
    op.create_index("ix_events_registration_closed", "events", ["registration_closed"], unique=False)
    op.create_index("ix_events_is_featured", "events", ["is_featured"], unique=False)

    op.create_table(
        "tournament_registrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("captain_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_name", sa.String(length=255), nullable=False),
        sa.Column("captain_first_name", sa.String(length=80), nullable=False),
        sa.Column("captain_last_name", sa.String(length=80), nullable=False),
        sa.Column("captain_phone", sa.String(length=40), nullable=False),
        sa.Column("players_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="paid"),
        sa.Column("payment_tx_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["captain_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.ForeignKeyConstraint(["payment_tx_id"], ["wallet_transactions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "captain_user_id", name="uq_tournament_event_captain"),
    )
    op.create_index(
        "ix_tournament_registrations_event_id",
        "tournament_registrations",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        "ix_tournament_registrations_captain_user_id",
        "tournament_registrations",
        ["captain_user_id"],
        unique=False,
    )

    op.create_table(
        "tournament_registration_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("registration_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("first_name", sa.String(length=80), nullable=False),
        sa.Column("last_name", sa.String(length=80), nullable=False),
        sa.Column("is_captain", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["registration_id"], ["tournament_registrations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tournament_registration_members_registration_id",
        "tournament_registration_members",
        ["registration_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tournament_registration_members_registration_id",
        table_name="tournament_registration_members",
    )
    op.drop_table("tournament_registration_members")

    op.drop_index("ix_tournament_registrations_captain_user_id", table_name="tournament_registrations")
    op.drop_index("ix_tournament_registrations_event_id", table_name="tournament_registrations")
    op.drop_table("tournament_registrations")

    op.drop_index("ix_events_is_featured", table_name="events")
    op.drop_index("ix_events_registration_closed", table_name="events")
    op.drop_index("ix_events_event_type", table_name="events")
    op.drop_column("events", "is_featured")
    op.drop_column("events", "registration_closed")
    op.drop_column("events", "registration_deadline")
    op.drop_column("events", "entry_fee_credits_team")
    op.drop_column("events", "description")
    op.drop_column("events", "event_type")
