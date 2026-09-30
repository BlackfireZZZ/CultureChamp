"""Record immutable metadata snapshots while editors structure candidates.

Revision ID: d357912468ac
Revises: c2468013579a
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d357912468ac"
down_revision: str | None = "c2468013579a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "source_revisions",
        sa.Column("metadata_version", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_table(
        "source_metadata_events",
        sa.Column("event_id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("reviewer_id", sa.String(length=100), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("version >= 0", name="metadata_version_nonnegative"),
        sa.ForeignKeyConstraint(["revision_id"], ["source_revisions.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("revision_id", "version", name="uq_source_metadata_revision_version"),
    )
    op.execute(sa.text("""
        INSERT INTO source_metadata_events
            (revision_id, version, reviewer_id, reason, description, tags, changed_at)
        SELECT r.id, 0, 'system:legacy-import', 'Captured metadata at intake',
               r.description,
               COALESCE((
                   SELECT jsonb_agg(
                       jsonb_build_object('kind', t.kind, 'value', t.value)
                       ORDER BY t.kind, t.value
                   )
                   FROM source_tags AS t WHERE t.revision_id = r.id
               ), '[]'::jsonb),
               r.captured_at
        FROM source_revisions AS r
    """))


def downgrade() -> None:
    op.drop_table("source_metadata_events")
    op.drop_column("source_revisions", "metadata_version")
