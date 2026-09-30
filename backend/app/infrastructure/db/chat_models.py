"""Private conversation, citation and shared model-quota records."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class ChatConversation(Base):
    __tablename__ = "chat_conversations"
    __table_args__ = (
        Index("ix_chat_conversations_owner_updated", "owner_id", "updated_at"),
        Index("ix_chat_conversations_expires", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"))
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChatTurn(Base):
    __tablename__ = "chat_turns"
    __table_args__ = (
        UniqueConstraint("conversation_id", "ordinal", name="uq_chat_turns_conversation_ordinal"),
        CheckConstraint("ordinal >= 0", name="ordinal"),
        CheckConstraint("attempt >= 1", name="attempt"),
        CheckConstraint("status IN ('pending', 'complete', 'failed')", name="status"),
        Index("ix_chat_turns_conversation", "conversation_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_conversations.id", ondelete="CASCADE")
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    user_text: Mapped[str] = mapped_column(Text, nullable=False)
    assistant_text: Mapped[str | None] = mapped_column(Text)
    evidence_status: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChatCitation(Base):
    __tablename__ = "chat_citations"
    __table_args__ = (
        UniqueConstraint("turn_id", "ordinal", name="uq_chat_citations_turn_ordinal"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    turn_id: Mapped[UUID] = mapped_column(ForeignKey("chat_turns.id", ondelete="CASCADE"))
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_revisions.id", ondelete="RESTRICT")
    )
    segment_id: Mapped[UUID] = mapped_column(ForeignKey("source_segments.id", ondelete="RESTRICT"))
    page: Mapped[int | None]
    section: Mapped[str | None] = mapped_column(Text)
    sheet: Mapped[str | None] = mapped_column(Text)
    table_name: Mapped[str | None] = mapped_column(Text)
    row_start: Mapped[int | None]
    row_end: Mapped[int | None]
    column_start: Mapped[int | None]
    column_end: Mapped[int | None]


class GenerationReservation(Base):
    __tablename__ = "generation_reservations"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'done', 'failed')", name="status"),
        Index("ix_generation_reservations_subject_created", "subject_id", "created_at"),
        Index("ix_generation_reservations_created", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    subject_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lease_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    input_tokens: Mapped[int | None]
    output_tokens: Mapped[int | None]


class GenerationAttempt(Base):
    __tablename__ = "generation_attempts"
    __table_args__ = (
        Index("ix_generation_attempts_subject_created", "subject_id", "created_at"),
        Index("ix_generation_attempts_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    reservation_id: Mapped[UUID] = mapped_column(
        ForeignKey("generation_reservations.id", ondelete="CASCADE")
    )
    subject_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
