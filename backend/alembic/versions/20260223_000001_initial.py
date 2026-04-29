"""initial

Revision ID: 20260223_000001
Revises:
Create Date: 2026-02-23 00:00:01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260223_000001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index("ix_users_role", "users", ["role"], unique=False)

    op.create_table(
        "sports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "venues",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column("hourly_rate", sa.Integer(), nullable=False),
        sa.Column("timezone", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["partner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_venues_partner_user_id", "venues", ["partner_user_id"], unique=False)
    op.create_index("ix_venues_city", "venues", ["city"], unique=False)

    op.create_table(
        "venue_sports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("venue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sport_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["sport_id"], ["sports.id"]),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("venue_id", "sport_id", name="uq_venue_sport"),
    )

    op.create_table(
        "venue_slots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("venue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_venue_slots_venue_id", "venue_slots", ["venue_id"], unique=False)
    op.create_index("ix_venue_slots_start_at", "venue_slots", ["start_at"], unique=False)
    op.create_index("ix_venue_slots_end_at", "venue_slots", ["end_at"], unique=False)

    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sport_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("venue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("required_players", sa.Integer(), nullable=False),
        sa.Column("teams_count", sa.Integer(), nullable=False),
        sa.Column("duration_hours", sa.Integer(), nullable=False),
        sa.Column("cost_credits_per_player", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["slot_id"], ["venue_slots.id"]),
        sa.ForeignKeyConstraint(["sport_id"], ["sports.id"]),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_created_by_user_id", "events", ["created_by_user_id"], unique=False)
    op.create_index("ix_events_sport_id", "events", ["sport_id"], unique=False)
    op.create_index("ix_events_venue_id", "events", ["venue_id"], unique=False)
    op.create_index("ix_events_slot_id", "events", ["slot_id"], unique=False)
    op.create_index("ix_events_start_at", "events", ["start_at"], unique=False)
    op.create_index("ix_events_end_at", "events", ["end_at"], unique=False)
    op.create_index("ix_events_status", "events", ["status"], unique=False)

    op.create_table(
        "wallet_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("balance", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_wallet_accounts_user_id", "wallet_accounts", ["user_id"], unique=False)

    op.create_table(
        "teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_number", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "team_number", name="uq_event_team_number"),
    )
    op.create_index("ix_teams_event_id", "teams", ["event_id"], unique=False)

    op.create_table(
        "event_participants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "user_id", name="uq_event_user"),
    )
    op.create_index("ix_event_participants_event_id", "event_participants", ["event_id"], unique=False)
    op.create_index("ix_event_participants_user_id", "event_participants", ["user_id"], unique=False)
    op.create_index("ix_event_participants_team_id", "event_participants", ["team_id"], unique=False)

    op.create_table(
        "wallet_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("wallet_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tx_type", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.ForeignKeyConstraint(["wallet_account_id"], ["wallet_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_wallet_transactions_wallet_account_id", "wallet_transactions", ["wallet_account_id"], unique=False)
    op.create_index("ix_wallet_transactions_event_id", "wallet_transactions", ["event_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_wallet_transactions_event_id", table_name="wallet_transactions")
    op.drop_index("ix_wallet_transactions_wallet_account_id", table_name="wallet_transactions")
    op.drop_table("wallet_transactions")
    op.drop_index("ix_event_participants_team_id", table_name="event_participants")
    op.drop_index("ix_event_participants_user_id", table_name="event_participants")
    op.drop_index("ix_event_participants_event_id", table_name="event_participants")
    op.drop_table("event_participants")
    op.drop_index("ix_teams_event_id", table_name="teams")
    op.drop_table("teams")
    op.drop_index("ix_wallet_accounts_user_id", table_name="wallet_accounts")
    op.drop_table("wallet_accounts")
    op.drop_index("ix_events_status", table_name="events")
    op.drop_index("ix_events_end_at", table_name="events")
    op.drop_index("ix_events_start_at", table_name="events")
    op.drop_index("ix_events_slot_id", table_name="events")
    op.drop_index("ix_events_venue_id", table_name="events")
    op.drop_index("ix_events_sport_id", table_name="events")
    op.drop_index("ix_events_created_by_user_id", table_name="events")
    op.drop_table("events")
    op.drop_index("ix_venue_slots_end_at", table_name="venue_slots")
    op.drop_index("ix_venue_slots_start_at", table_name="venue_slots")
    op.drop_index("ix_venue_slots_venue_id", table_name="venue_slots")
    op.drop_table("venue_slots")
    op.drop_table("venue_sports")
    op.drop_index("ix_venues_city", table_name="venues")
    op.drop_index("ix_venues_partner_user_id", table_name="venues")
    op.drop_table("venues")
    op.drop_table("sports")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
