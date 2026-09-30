"""Persist owned conversations and shared generation reservations.

Revision ID: a3452e9b6577
Revises: f023fd810bc1
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a3452e9b6577"
down_revision: str | None = "f023fd810bc1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_conversations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "owner_id", sa.Uuid(), sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_chat_conversations_owner_updated", "chat_conversations", ["owner_id", "updated_at"]
    )
    op.create_index("ix_chat_conversations_expires", "chat_conversations", ["expires_at"])
    op.create_table(
        "chat_turns",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Uuid(),
            sa.ForeignKey("chat_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("user_text", sa.Text(), nullable=False),
        sa.Column("assistant_text", sa.Text()),
        sa.Column("evidence_status", sa.String(32)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("ordinal >= 0", name=op.f("ck_chat_turns_ordinal")),
        sa.CheckConstraint("attempt >= 1", name=op.f("ck_chat_turns_attempt")),
        sa.CheckConstraint(
            "status IN ('pending', 'complete', 'failed')", name=op.f("ck_chat_turns_status")
        ),
        sa.UniqueConstraint(
            "conversation_id", "ordinal", name="uq_chat_turns_conversation_ordinal"
        ),
    )
    op.create_index("ix_chat_turns_conversation", "chat_turns", ["conversation_id"])
    op.create_table(
        "chat_citations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "turn_id", sa.Uuid(), sa.ForeignKey("chat_turns.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column(
            "revision_id",
            sa.Uuid(),
            sa.ForeignKey("source_revisions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "segment_id",
            sa.Uuid(),
            sa.ForeignKey("source_segments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("page", sa.Integer()),
        sa.Column("section", sa.Text()),
        sa.Column("sheet", sa.Text()),
        sa.Column("table_name", sa.Text()),
        sa.Column("row_start", sa.Integer()),
        sa.Column("row_end", sa.Integer()),
        sa.Column("column_start", sa.Integer()),
        sa.Column("column_end", sa.Integer()),
        sa.UniqueConstraint("turn_id", "ordinal", name="uq_chat_citations_turn_ordinal"),
    )
    op.create_table(
        "generation_reservations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "subject_id",
            sa.Uuid(),
            sa.ForeignKey("accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.CheckConstraint(
            "status IN ('active', 'done', 'failed')", name=op.f("ck_generation_reservations_status")
        ),
    )
    op.create_index(
        "ix_generation_reservations_subject_created",
        "generation_reservations",
        ["subject_id", "created_at"],
    )
    op.create_index("ix_generation_reservations_created", "generation_reservations", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_generation_reservations_created", table_name="generation_reservations")
    op.drop_index(
        "ix_generation_reservations_subject_created", table_name="generation_reservations"
    )
    op.drop_table("generation_reservations")
    op.drop_table("chat_citations")
    op.drop_index("ix_chat_turns_conversation", table_name="chat_turns")
    op.drop_table("chat_turns")
    op.drop_index("ix_chat_conversations_expires", table_name="chat_conversations")
    op.drop_index("ix_chat_conversations_owner_updated", table_name="chat_conversations")
    op.drop_table("chat_conversations")
