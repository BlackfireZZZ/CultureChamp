"""Count every reserved model attempt against daily limits.

Revision ID: b482f736c1da
Revises: f128c768b4ae
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b482f736c1da"
down_revision: str | None = "f128c768b4ae"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "generation_attempts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("reservation_id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["reservation_id"], ["generation_reservations.id"],
            name=op.f("fk_generation_attempts_reservation_id_generation_reservations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"], ["accounts.id"],
            name=op.f("fk_generation_attempts_subject_id_accounts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_generation_attempts")),
    )
    op.create_index(
        "ix_generation_attempts_subject_created",
        "generation_attempts", ["subject_id", "created_at"],
    )
    op.create_index("ix_generation_attempts_created", "generation_attempts", ["created_at"])
    op.execute(
        "INSERT INTO generation_attempts (reservation_id, subject_id, created_at) "
        "SELECT id, subject_id, created_at FROM generation_reservations"
    )


def downgrade() -> None:
    op.drop_index("ix_generation_attempts_created", table_name="generation_attempts")
    op.drop_index(
        "ix_generation_attempts_subject_created", table_name="generation_attempts"
    )
    op.drop_table("generation_attempts")
