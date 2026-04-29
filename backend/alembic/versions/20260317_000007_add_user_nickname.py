"""add_user_nickname

Revision ID: 20260317_000007
Revises: 20260316_000006
Create Date: 2026-03-17 00:00:07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260317_000007"
down_revision: Union[str, None] = "20260316_000006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("nickname", sa.String(length=15), nullable=True))
    op.create_index("ix_users_nickname", "users", ["nickname"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_nickname", table_name="users")
    op.drop_column("users", "nickname")
