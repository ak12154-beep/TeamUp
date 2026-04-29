"""onboarding_score_fields

Revision ID: 20260316_000006
Revises: 20260305_000005
Create Date: 2026-03-16 00:00:06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260316_000006"
down_revision: Union[str, None] = "20260305_000005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("onboarding_score", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("onboarding_level_label", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("onboarding_summary", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("onboarding_sport_focus", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "onboarding_completed_at")
    op.drop_column("users", "onboarding_sport_focus")
    op.drop_column("users", "onboarding_summary")
    op.drop_column("users", "onboarding_level_label")
    op.drop_column("users", "onboarding_score")
