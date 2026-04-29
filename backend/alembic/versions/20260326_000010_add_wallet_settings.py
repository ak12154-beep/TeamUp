"""add wallet settings

Revision ID: 20260326_000010
Revises: 20260317_000009
Create Date: 2026-03-26 00:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260326_000010"
down_revision = "20260317_000009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wallet_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("qr_image_url", sa.String(length=500), nullable=True),
        sa.Column("payment_url", sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("wallet_settings")