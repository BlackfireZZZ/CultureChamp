"""Keep reported usage for each application-level model attempt.

Revision ID: ab83f0c214d7
Revises: f406c9a2b7e1
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "ab83f0c214d7"
down_revision: str | None = "f406c9a2b7e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("generation_attempts", sa.Column("accepted", sa.Boolean()))
    op.add_column("generation_attempts", sa.Column("input_tokens", sa.Integer()))
    op.add_column("generation_attempts", sa.Column("output_tokens", sa.Integer()))


def downgrade() -> None:
    op.drop_column("generation_attempts", "output_tokens")
    op.drop_column("generation_attempts", "input_tokens")
    op.drop_column("generation_attempts", "accepted")
