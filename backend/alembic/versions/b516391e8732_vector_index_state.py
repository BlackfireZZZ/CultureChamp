"""Record completed vector indexing by exact revision and model.

Revision ID: b516391e8732
Revises: a3452e9b6577
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b516391e8732"
down_revision: str | None = "a3452e9b6577"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_vector_indexes",
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("model_id", sa.Text(), nullable=False),
        sa.Column(
            "indexed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["revision_id"], ["source_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("revision_id"),
    )


def downgrade() -> None:
    op.drop_table("source_vector_indexes")
