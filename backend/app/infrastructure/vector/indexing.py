"""Replayable indexing of approved, exact source revisions."""

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.db.source_models import (
    SourceDecision,
    SourceProcessing,
    SourceRevision,
    SourceSegment,
    SourceVectorIndex,
)
from app.infrastructure.vector.text_vectors import MODEL_ID, QdrantTextIndex


class ApprovedTextIndexer:
    def __init__(
        self, factory: async_sessionmaker[AsyncSession], index: QdrantTextIndex
    ) -> None:
        self.factory = factory
        self.index = index
        self._audit_cursor: UUID | None = None

    async def index_one(self) -> UUID | None:
        if not await self.index.collection_exists():
            # The SQL markers refer to a lost index generation. Clear them before
            # creating the collection so approved revisions are replayed.
            async with self.factory.begin() as session:
                await session.execute(delete(SourceVectorIndex))
            await self.index.ensure_collection()
        latest_event = (
            select(func.max(SourceDecision.event_id))
            .where(SourceDecision.revision_id == SourceRevision.id)
            .correlate(SourceRevision)
            .scalar_subquery()
        )
        async with self.factory() as session:
            revision_id = await session.scalar(
                select(SourceRevision.id)
                .join(SourceProcessing, SourceProcessing.revision_id == SourceRevision.id)
                .join(SourceDecision, SourceDecision.revision_id == SourceRevision.id)
                .outerjoin(SourceVectorIndex, SourceVectorIndex.revision_id == SourceRevision.id)
                .where(
                    SourceProcessing.state == "review_pending",
                    SourceDecision.event_id == latest_event,
                    SourceDecision.kind == "approve",
                    SourceDecision.user_text.is_(True),
                    SourceDecision.sensitivity_cleared.is_(True),
                    (SourceVectorIndex.revision_id.is_(None))
                    | (SourceVectorIndex.model_id != MODEL_ID),
                )
                .order_by(SourceRevision.captured_at)
                .limit(1)
            )
            if revision_id is None:
                return None
            segments = (
                await session.scalars(
                    select(SourceSegment)
                    .where(SourceSegment.revision_id == revision_id)
                    .order_by(SourceSegment.ordinal)
                )
            ).all()
        await self.index.upsert([(s.id, revision_id, s.text) for s in segments])
        async with self.factory.begin() as session:
            record = await session.get(SourceVectorIndex, revision_id)
            if record is None:
                session.add(SourceVectorIndex(revision_id=revision_id, model_id=MODEL_ID))
            else:
                record.model_id = MODEL_ID
        return revision_id

    async def remove_revoked_one(self) -> UUID | None:
        latest_event = (
            select(func.max(SourceDecision.event_id))
            .where(SourceDecision.revision_id == SourceVectorIndex.revision_id)
            .correlate(SourceVectorIndex)
            .scalar_subquery()
        )
        async with self.factory() as session:
            revision_id = await session.scalar(
                select(SourceVectorIndex.revision_id)
                .join(SourceDecision, SourceDecision.revision_id == SourceVectorIndex.revision_id)
                .where(
                    SourceDecision.event_id == latest_event,
                    SourceDecision.kind == "revoke",
                )
                .limit(1)
            )
            if revision_id is None:
                return None
            segment_ids = (
                await session.scalars(
                    select(SourceSegment.id).where(SourceSegment.revision_id == revision_id)
                )
            ).all()
        await self.index.delete(segment_ids)
        async with self.factory.begin() as session:
            record = await session.get(SourceVectorIndex, revision_id)
            if record is not None:
                await session.delete(record)
        return revision_id

    async def audit_one(self) -> UUID | None:
        """Check one approved revision's exact point set and queue a missing set for replay."""
        latest_event = (
            select(func.max(SourceDecision.event_id))
            .where(SourceDecision.revision_id == SourceVectorIndex.revision_id)
            .correlate(SourceVectorIndex)
            .scalar_subquery()
        )
        async with self.factory() as session:
            statement = (
                select(SourceVectorIndex.revision_id)
                .join(SourceDecision, SourceDecision.revision_id == SourceVectorIndex.revision_id)
                .where(
                    SourceVectorIndex.model_id == MODEL_ID,
                    SourceDecision.event_id == latest_event,
                    SourceDecision.kind == "approve",
                    SourceDecision.user_text.is_(True),
                    SourceDecision.sensitivity_cleared.is_(True),
                )
                .order_by(SourceVectorIndex.revision_id)
                .limit(1)
            )
            revision_id = None
            if self._audit_cursor is not None:
                revision_id = await session.scalar(
                    statement.where(SourceVectorIndex.revision_id > self._audit_cursor)
                )
            if revision_id is None:
                revision_id = await session.scalar(statement)
            if revision_id is None:
                self._audit_cursor = None
                return None
            segment_ids = (
                await session.scalars(
                    select(SourceSegment.id).where(SourceSegment.revision_id == revision_id)
                )
            ).all()
        self._audit_cursor = revision_id
        if await self.index.has_revision_points(revision_id, segment_ids):
            return None
        async with self.factory.begin() as session:
            record = await session.get(SourceVectorIndex, revision_id)
            if record is not None:
                await session.delete(record)
        return revision_id
