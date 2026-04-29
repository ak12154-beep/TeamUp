"""add tournament team slogans

Revision ID: 20260405_000011
Revises: 20260405_000010
Create Date: 2026-04-05 00:11:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260405_000011"
down_revision = "20260405_000010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tournament_registrations", sa.Column("team_slogan", sa.String(length=280), nullable=True))


def downgrade() -> None:
    op.drop_column("tournament_registrations", "team_slogan")
