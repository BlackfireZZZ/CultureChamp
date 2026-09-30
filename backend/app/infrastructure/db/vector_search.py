"""Vector candidates rechecked against authoritative exact-revision decisions."""

from uuid import UUID

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


def _empty_or_pending(has_pending: bool) -> tuple[EvidenceSegment, ...]:
    if has_pending:
        raise VectorUnavailable("Approved evidence is awaiting indexing")
    return ()


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
        eligible = (
            select(SourceRevision.id)
            .join(SourceProcessing, SourceProcessing.revision_id == SourceRevision.id)
            .join(SourceDecision, SourceDecision.revision_id == SourceRevision.id)
            .join(SourceVectorIndex, SourceVectorIndex.revision_id == SourceRevision.id)
            .where(
                SourceProcessing.state == "review_pending",
                SourceDecision.event_id == latest_event,
                SourceDecision.kind == "approve",
                SourceDecision.user_text.is_(True),
                SourceDecision.sensitivity_cleared.is_(True),
                SourceVectorIndex.model_id == MODEL_ID,
            )
        )
        if for_provider:
            eligible = eligible.where(SourceDecision.provider_transfer.is_(True))
        for kind, value in (("region", region), ("people", people)):
            if value is not None:
                tag_exists = (
                    select(SourceTag.id)
                    .where(
                        SourceTag.revision_id == SourceRevision.id,
                        SourceTag.kind == kind,
                        SourceTag.value == value,
                    )
                    .exists()
                )
                eligible = eligible.where(tag_exists)
                pending = pending.where(tag_exists)
        async with self.factory() as session:
            has_pending = await session.scalar(pending) is not None
            allowed_revision_ids = (await session.scalars(eligible)).all()
        if not allowed_revision_ids:
            return _empty_or_pending(has_pending)
        # A stale or revoked vector point has no authority to expose a source.
        candidates = tuple(
            (segment_id, score)
            for segment_id, score in await self.index.query(
                query, max(100, limit * 20), allowed_revision_ids=allowed_revision_ids
            )
            if score >= MIN_TEXT_COSINE
        )
        if not candidates:
            return _empty_or_pending(has_pending)
        scores = {segment_id: score for segment_id, score in candidates}
        statement = (
            select(SourceSegment, SourceRevision)
            .join(SourceRevision, SourceRevision.id == SourceSegment.revision_id)
            .join(SourceProcessing, SourceProcessing.revision_id == SourceRevision.id)
            .join(SourceDecision, SourceDecision.revision_id == SourceRevision.id)
            .where(
                SourceSegment.id.in_(scores),
                SourceSegment.included.is_(True),
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
            revision_ids = {revision.id for _, revision in rows}
            tags = (
                (
                    await session.scalars(
                        select(SourceTag)
                        .where(
                            SourceTag.revision_id.in_(revision_ids),
                            SourceTag.kind.in_(("region", "people", "period")),
                        )
                        .order_by(SourceTag.kind, SourceTag.value)
                    )
                ).all()
                if revision_ids else []
            )
        by_id = {segment.id: (segment, revision) for segment, revision in rows}
        tags_by_revision: dict[UUID, list[tuple[str, str]]] = {}
        for tag in tags:
            tags_by_revision.setdefault(tag.revision_id, []).append((tag.kind, tag.value))
        found = tuple(
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
                context_tags=tuple(tags_by_revision.get(revision.id, ())),
            )
            for segment_id, score in candidates
            if segment_id in by_id
            for segment, revision in (by_id[segment_id],)
        )[:limit]
        return found if found else _empty_or_pending(has_pending)
