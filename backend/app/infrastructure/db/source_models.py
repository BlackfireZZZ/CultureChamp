"""Persistence records for exact source revisions and locators."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    origin_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class SourceRevision(Base):
    __tablename__ = "source_revisions"
    __table_args__ = (
        UniqueConstraint("source_id", "sha256", name="uq_source_revisions_source_hash"),
        UniqueConstraint("storage_key", name="uq_source_revisions_storage_key"),
        CheckConstraint("byte_size > 0", name="positive_byte_size"),
        CheckConstraint("length(sha256) = 64", name="sha256_length"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(ForeignKey("sources.id", ondelete="RESTRICT"))
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_size: Mapped[int] = mapped_column(nullable=False)
    media_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    creator: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(35))
    period_note: Mapped[str | None] = mapped_column(Text)
    rights_note: Mapped[str | None] = mapped_column(Text)
    captured_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class SourceTag(Base):
    __tablename__ = "source_tags"
    __table_args__ = (
        UniqueConstraint("revision_id", "kind", "value", name="uq_source_tags_revision_kind_value"),
        CheckConstraint(
            "kind IN ('region', 'people', 'period', 'topic', 'sensitivity')", name="kind"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_revisions.id", ondelete="RESTRICT")
    )
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)


class SourceSegment(Base):
    __tablename__ = "source_segments"
    __table_args__ = (
        UniqueConstraint("revision_id", "ordinal", name="uq_source_segments_revision_ordinal"),
        CheckConstraint("ordinal >= 0", name="ordinal"),
        CheckConstraint("kind IN ('prose', 'table')", name="kind"),
        CheckConstraint("page IS NULL OR page >= 1", name="page"),
        CheckConstraint("row_start IS NULL OR row_start >= 1", name="row_start"),
        CheckConstraint("row_end IS NULL OR row_end >= row_start", name="row_end"),
        CheckConstraint("column_start IS NULL OR column_start >= 1", name="column_start"),
        CheckConstraint("column_end IS NULL OR column_end >= column_start", name="column_end"),
        CheckConstraint(
            "(row_start IS NULL AND row_end IS NULL AND "
            "column_start IS NULL AND column_end IS NULL) "
            "OR (row_start IS NOT NULL AND row_end IS NOT NULL "
            "AND column_start IS NOT NULL "
            "AND column_end IS NOT NULL AND (sheet IS NOT NULL OR table_name IS NOT NULL))",
            name="table_range_complete",
        ),
        CheckConstraint("page IS NOT NULL OR row_start IS NOT NULL", name="has_locator"),
        Index("ix_source_segments_revision_page", "revision_id", "page"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_revisions.id", ondelete="RESTRICT")
    )
    ordinal: Mapped[int] = mapped_column(nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    page: Mapped[int | None]
    section: Mapped[str | None] = mapped_column(Text)
    sheet: Mapped[str | None] = mapped_column(Text)
    table_name: Mapped[str | None] = mapped_column(Text)
    row_start: Mapped[int | None]
    row_end: Mapped[int | None]
    column_start: Mapped[int | None]
    column_end: Mapped[int | None]


class SourceDecision(Base):
    __tablename__ = "source_decisions"
    __table_args__ = (
        CheckConstraint("kind IN ('approve', 'revoke')", name="kind"),
        Index("ix_source_decisions_revision_event", "revision_id", "event_id"),
    )

    event_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_revisions.id", ondelete="RESTRICT")
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    reviewer_id: Mapped[str] = mapped_column(String(100), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_url: Mapped[str] = mapped_column(Text, nullable=False)
    user_text: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    original_file: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    provider_transfer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sensitivity_cleared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    decided_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
