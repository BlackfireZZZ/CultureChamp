"""Audit preapproval exclusion of extracted source segments.

Revision ID: f406c9a2b7e1
Revises: e9278d4a6a1f
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "f406c9a2b7e1"
down_revision: str | None = "e9278d4a6a1f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "source_revisions",
        sa.Column("segment_review_version", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "source_segments",
        sa.Column("included", sa.Boolean(), server_default="true", nullable=False),
    )
    op.create_table(
        "source_segment_review_events",
        sa.Column("event_id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("reviewer_id", sa.String(length=100), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("excluded_segment_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("version > 0", name="version_positive"),
        sa.ForeignKeyConstraint(["revision_id"], ["source_revisions.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("revision_id", "version", name="uq_source_segment_review_version"),
    )


def downgrade() -> None:
    op.drop_table("source_segment_review_events")
    op.drop_column("source_segments", "included")
    op.drop_column("source_revisions", "segment_review_version")
