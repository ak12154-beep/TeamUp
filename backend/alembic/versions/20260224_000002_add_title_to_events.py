"""add_title_to_events

Revision ID: 20260224_000002
Revises: 20260223_000001
Create Date: 2026-02-24 00:00:02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260224_000002"
down_revision: Union[str, None] = "20260223_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("events", sa.Column("title", sa.String(length=255), nullable=True))
    # Set default title for existing events
    op.execute("UPDATE events SET title = 'Untitled Event' WHERE title IS NULL")
    op.alter_column("events", "title", nullable=False)


def downgrade() -> None:
    op.drop_column("events", "title")
