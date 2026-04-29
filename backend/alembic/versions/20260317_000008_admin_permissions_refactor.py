"""admin_permissions_refactor

Revision ID: 20260317_000008
Revises: 20260317_000007
Create Date: 2026-03-17 00:00:08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
revision: str = "20260317_000008"
down_revision: Union[str, None] = "20260317_000007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.create_index("ix_users_is_admin", "users", ["is_admin"], unique=False)

    bind = op.get_bind()
    meta = sa.MetaData()
    users = sa.Table(
        "users",
        meta,
        sa.Column("role", sa.String()),
        sa.Column("is_admin", sa.Boolean()),
    )

    bind.execute(sa.update(users).where(users.c.role == "admin").values(is_admin=True))

    bind.execute(sa.update(users).where(users.c.role == "admin").values(role="player"))

    bind.execute(sa.text("ALTER TABLE users ALTER COLUMN is_admin DROP DEFAULT"))


def downgrade() -> None:
    op.drop_index("ix_users_is_admin", table_name="users")
    op.drop_column("users", "is_admin")
