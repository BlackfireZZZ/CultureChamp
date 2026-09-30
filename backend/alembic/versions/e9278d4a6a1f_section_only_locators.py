"""Permit section-only locators for immutable plain-text revisions.

Revision ID: e9278d4a6a1f
Revises: b482f736c1da
"""

from collections.abc import Sequence

from alembic import op

revision: str = "e9278d4a6a1f"
down_revision: str | None = "b482f736c1da"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_source_segments_has_locator"), "source_segments", type_="check")
    op.create_check_constraint(
        op.f("ck_source_segments_has_locator"),
        "source_segments",
        "page IS NOT NULL OR (section IS NOT NULL AND btrim(section) <> '') "
        "OR row_start IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_source_segments_has_locator"), "source_segments", type_="check")
    op.create_check_constraint(
        op.f("ck_source_segments_has_locator"),
        "source_segments",
        "page IS NOT NULL OR row_start IS NOT NULL",
    )
