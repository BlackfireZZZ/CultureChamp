"""Record an optional starter choice on an existing chat request.

Revision ID: c019e814c347
Revises: ab83f0c214d7
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c019e814c347"
down_revision: str | None = "ab83f0c214d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("chat_turns", sa.Column("starter_id", sa.String(length=5)))
    op.create_check_constraint(
        "ck_chat_turns_starter_id",
        "chat_turns",
        "starter_id IS NULL OR starter_id IN "
        "('UC-01', 'UC-02', 'UC-03', 'UC-04', 'UC-05', 'UC-06')",
    )
    op.create_index("ix_chat_turns_created_at", "chat_turns", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_chat_turns_created_at", table_name="chat_turns")
    op.drop_constraint("ck_chat_turns_starter_id", "chat_turns", type_="check")
    op.drop_column("chat_turns", "starter_id")
