"""Vector candidates rechecked against authoritative exact-revision decisions."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.retrieval import EvidenceSegment
from app.domain.sources import Locator
from app.infrastructure.db.source_models import (
    SourceDecision,
    SourceProcessing,
    SourceRevision,
    SourceSegment,
    SourceTag,
    SourceVectorIndex,
)
from app.infrastructure.vector.text_vectors import (
    MIN_TEXT_COSINE,
    MODEL_ID,
    QdrantTextIndex,
    VectorUnavailable,
)


class SqlGovernedVectorSearch:
    def __init__(
        self, factory: async_sessionmaker[AsyncSession], index: QdrantTextIndex
    ) -> None:
        self.factory = factory
        self.index = index

    async def search(
        self,
        query: str,
        *,
        limit: int,
        region: str | None,
        people: str | None,
        for_provider: bool,
    ) -> tuple[EvidenceSegment, ...]:
        latest_event = (
            select(func.max(SourceDecision.event_id))
            .where(SourceDecision.revision_id == SourceRevision.id)
            .correlate(SourceRevision)
            .scalar_subquery()
        )
        pending = (
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
            .limit(1)
        )
        if for_provider:
            pending = pending.where(SourceDecision.provider_transfer.is_(True))
        async with self.factory() as session:
            if await session.scalar(pending) is not None:
                raise VectorUnavailable("Approved evidence is awaiting indexing")
        # A stale or revoked vector point has no authority to expose a source.
        candidates = tuple(
            (segment_id, score)
            for segment_id, score in await self.index.query(query, max(100, limit * 20))
            if score >= MIN_TEXT_COSINE
        )
        if not candidates:
            return ()
        scores = {segment_id: score for segment_id, score in candidates}
        statement = (
            select(SourceSegment, SourceRevision)
            .join(SourceRevision, SourceRevision.id == SourceSegment.revision_id)
            .join(SourceProcessing, SourceProcessing.revision_id == SourceRevision.id)
            .join(SourceDecision, SourceDecision.revision_id == SourceRevision.id)
            .where(
                SourceSegment.id.in_(scores),
                SourceProcessing.state == "review_pending",
                SourceDecision.event_id == latest_event,
                SourceDecision.kind == "approve",
                SourceDecision.user_text.is_(True),
                SourceDecision.sensitivity_cleared.is_(True),
            )
        )
        if for_provider:
            statement = statement.where(SourceDecision.provider_transfer.is_(True))
        for kind, value in (("region", region), ("people", people)):
            if value is not None:
                statement = statement.where(
                    select(SourceTag.id)
                    .where(
                        SourceTag.revision_id == SourceRevision.id,
                        SourceTag.kind == kind,
                        SourceTag.value == value,
                    )
                    .exists()
                )
        async with self.factory() as session:
            rows = (await session.execute(statement)).all()
        by_id = {segment.id: (segment, revision) for segment, revision in rows}
        return tuple(
            EvidenceSegment(
                revision_id=revision.id,
                segment_id=segment.id,
                title=revision.title,
                creator=revision.creator,
                locator=Locator(
                    page=segment.page,
                    section=segment.section,
                    sheet=segment.sheet,
                    table=segment.table_name,
                    row_start=segment.row_start,
                    row_end=segment.row_end,
                    column_start=segment.column_start,
                    column_end=segment.column_end,
                ),
                text=segment.text,
                score=score,
            )
            for segment_id, score in candidates
            if segment_id in by_id
            for segment, revision in (by_id[segment_id],)
        )[:limit]
