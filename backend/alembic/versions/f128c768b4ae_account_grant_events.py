"""Record who created a pilot account and assigned its initial role.

Revision ID: f128c768b4ae
Revises: d357912468ac
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f128c768b4ae"
down_revision: str | None = "d357912468ac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "account_grant_events",
        sa.Column("event_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("role IN ('user', 'admin')", name=op.f("ck_account_grant_events_role")),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["accounts.id"], name=op.f("fk_account_grant_events_actor_id_accounts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"], ["accounts.id"],
            name=op.f("fk_account_grant_events_account_id_accounts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("event_id", name=op.f("pk_account_grant_events")),
    )
    op.create_index(
        "ix_account_grant_events_account_id", "account_grant_events", ["account_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_account_grant_events_account_id", table_name="account_grant_events")
    op.drop_table("account_grant_events")
