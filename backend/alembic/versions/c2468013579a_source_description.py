"""Capture an optional, curator-written description on each source revision.

Revision ID: c2468013579a
Revises: b516391e8732
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c2468013579a"
down_revision: str | None = "b516391e8732"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("source_revisions", sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("source_revisions", "description")
