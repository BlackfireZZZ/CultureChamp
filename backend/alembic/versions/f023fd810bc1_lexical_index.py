"""Index source segments for the measured lexical baseline.

Revision ID: f023fd810bc1
Revises: df612efc24ce
"""

from collections.abc import Sequence

from alembic import op

revision: str = "f023fd810bc1"
down_revision: str | None = "df612efc24ce"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX ix_source_segments_search_russian "
        "ON source_segments USING GIN (to_tsvector('russian'::regconfig, text))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX ix_source_segments_search_russian")
