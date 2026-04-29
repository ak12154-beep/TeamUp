"""backend_safety_hardening

Revision ID: 20260301_000004
Revises: 20260224_000003
Create Date: 2026-03-01 00:00:04
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260301_000004"
down_revision: Union[str, None] = "20260224_000003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_wallet_accounts_balance_non_negative",
        "wallet_accounts",
        "balance >= 0",
    )
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(
        """
        ALTER TABLE events
        ADD CONSTRAINT events_no_active_overlap_per_venue
        EXCLUDE USING gist (
            venue_id WITH =,
            tstzrange(start_at, end_at, '[)') WITH &&
        )
        WHERE (status = 'active')
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE events DROP CONSTRAINT IF EXISTS events_no_active_overlap_per_venue")
    op.drop_constraint(
        "ck_wallet_accounts_balance_non_negative",
        "wallet_accounts",
        type_="check",
    )
