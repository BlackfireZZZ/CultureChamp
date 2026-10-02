"""Store a current rating and optional comment on each completed answer.

Revision ID: f6c0e1a2b3d4
Revises: d2a540f9c518
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f6c0e1a2b3d4"
down_revision: str | None = "d2a540f9c518"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("chat_turns", sa.Column("rating", sa.String(length=4)))
    op.add_column("chat_turns", sa.Column("feedback_comment", sa.Text()))
    op.add_column("chat_turns", sa.Column("feedback_at", sa.DateTime(timezone=True)))
    op.create_check_constraint(
        "ck_chat_turns_rating",
        "chat_turns",
        "rating IS NULL OR (rating IN ('up', 'down') AND status = 'complete')",
    )
    op.create_check_constraint(
        "ck_chat_turns_feedback_comment",
        "chat_turns",
        "feedback_comment IS NULL OR "
        "(rating IS NOT NULL AND char_length(feedback_comment) <= 1000)",
    )
    op.create_index("ix_chat_turns_feedback_at", "chat_turns", ["feedback_at"])


def downgrade() -> None:
    op.drop_index("ix_chat_turns_feedback_at", table_name="chat_turns")
    op.drop_constraint("ck_chat_turns_feedback_comment", "chat_turns", type_="check")
    op.drop_constraint("ck_chat_turns_rating", "chat_turns", type_="check")
    op.drop_column("chat_turns", "feedback_at")
    op.drop_column("chat_turns", "feedback_comment")
    op.drop_column("chat_turns", "rating")
