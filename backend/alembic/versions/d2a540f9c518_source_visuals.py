"""Record private embedded images and their visual index generation.

Revision ID: d2a540f9c518
Revises: c019e814c347
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d2a540f9c518"
down_revision: str | None = "c019e814c347"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_visuals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["revision_id"], ["source_revisions.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("revision_id", "page", "ordinal", name="uq_source_visual_locator"),
        sa.CheckConstraint("page >= 1", name="ck_source_visuals_page_positive"),
        sa.CheckConstraint("ordinal >= 0", name="ck_source_visuals_ordinal_nonnegative"),
        sa.CheckConstraint("length(sha256) = 64", name="ck_source_visuals_sha256_length"),
    )
    op.create_index("ix_source_visuals_revision", "source_visuals", ["revision_id"])
    op.create_table(
        "source_visual_indexes",
        sa.Column("revision_id", sa.Uuid(), primary_key=True),
        sa.Column("model_id", sa.Text(), nullable=False),
        sa.Column(
            "indexed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["revision_id"], ["source_revisions.id"], ondelete="RESTRICT"),
    )


def downgrade() -> None:
    op.drop_table("source_visual_indexes")
    op.drop_index("ix_source_visuals_revision", table_name="source_visuals")
    op.drop_table("source_visuals")
