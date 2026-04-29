"""registration_verification_flow

Revision ID: 20260305_000005
Revises: 20260301_000004
Create Date: 2026-03-05 00:00:05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260305_000005"
down_revision: Union[str, None] = "20260301_000004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("first_name", sa.String(length=80), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(length=80), nullable=True))
    op.add_column("users", sa.Column("birth_date", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.text("true")))

    op.execute("UPDATE users SET first_name = 'TeamUp' WHERE first_name IS NULL")
    op.execute("UPDATE users SET last_name = 'User' WHERE last_name IS NULL")
    op.execute("UPDATE users SET birth_date = DATE '1990-01-01' WHERE birth_date IS NULL")
    op.execute("UPDATE users SET email_verified = true WHERE email_verified IS NULL")

    op.alter_column("users", "first_name", nullable=False)
    op.alter_column("users", "last_name", nullable=False)
    op.alter_column("users", "birth_date", nullable=False)

    op.create_table(
        "email_verification_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_verification_codes_email", "email_verification_codes", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_email_verification_codes_email", table_name="email_verification_codes")
    op.drop_table("email_verification_codes")

    op.drop_column("users", "email_verified")
    op.drop_column("users", "birth_date")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
