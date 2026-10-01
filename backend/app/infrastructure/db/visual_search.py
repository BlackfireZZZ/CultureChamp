"""Authorize exact PDF revisions before and after visual vector ranking."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.db.source_models import (
    SourceDecision,
    SourceProcessing,
    SourceRevision,
    SourceSegment,
    SourceTag,
    SourceVisual,
    SourceVisualIndex,
)
from app.infrastructure.vector.visual_vectors import MODEL_ID, QdrantVisualIndex


@dataclass(frozen=True, slots=True)
class VisualResult:
    revision_id: UUID
    image_id: UUID
    page: int
    title: str
    creator: str | None
    score: float


class SqlVisualSearch:
    def __init__(self, factory: async_sessionmaker[AsyncSession], index: QdrantVisualIndex):
        self.factory = factory
        self.index = index

    async def search(
        self, query: str, *, limit: int = 8, region: str | None = None, people: str | None = None
    ) -> list[VisualResult]:
        latest = (
            select(func.max(SourceDecision.event_id))
            .where(SourceDecision.revision_id == SourceRevision.id)
            .correlate(SourceRevision)
            .scalar_subquery()
        )
        excluded = (
            select(SourceSegment.id)
            .where(
                SourceSegment.revision_id == SourceRevision.id, SourceSegment.included.is_(False)
            )
            .exists()
        )
        criteria = [
            SourceProcessing.state == "review_pending",
            SourceRevision.media_type == "application/pdf",
            SourceDecision.event_id == latest,
            SourceDecision.kind == "approve",
            SourceDecision.user_text.is_(True),
            SourceDecision.original_file.is_(True),
            SourceDecision.sensitivity_cleared.is_(True),
            SourceVisualIndex.model_id == MODEL_ID,
            ~excluded,
        ]
        for kind, value in (("region", region), ("people", people)):
            if value is not None:
                criteria.append(
                    select(SourceTag.id)
                    .where(
                        SourceTag.revision_id == SourceRevision.id,
                        SourceTag.kind == kind,
                        SourceTag.value == value,
                    )
                    .exists()
                )
        base = (
            select(SourceRevision.id)
            .join(SourceProcessing, SourceProcessing.revision_id == SourceRevision.id)
            .join(SourceDecision, SourceDecision.revision_id == SourceRevision.id)
            .join(SourceVisualIndex, SourceVisualIndex.revision_id == SourceRevision.id)
            .where(*criteria)
        )
        async with self.factory() as session:
            revisions = list((await session.scalars(base)).all())
        if not revisions:
            return []
        candidates = await self.index.query(query, revisions, max(40, limit * 5))
        if not candidates:
            return []
        scores = {image_id: score for image_id, score in candidates}
        async with self.factory() as session:
            rows = (
                await session.execute(
                    select(SourceVisual, SourceRevision)
                    .join(SourceRevision, SourceRevision.id == SourceVisual.revision_id)
                    .join(SourceProcessing, SourceProcessing.revision_id == SourceRevision.id)
                    .join(SourceDecision, SourceDecision.revision_id == SourceRevision.id)
                    .join(SourceVisualIndex, SourceVisualIndex.revision_id == SourceRevision.id)
                    .where(SourceVisual.id.in_(scores), *criteria)
                )
            ).all()
        by_id = {image.id: (image, revision) for image, revision in rows}
        return [
            VisualResult(revision.id, image.id, image.page, revision.title, revision.creator, score)
            for image_id, score in candidates
            if image_id in by_id
            for image, revision in (by_id[image_id],)
        ][:limit]
