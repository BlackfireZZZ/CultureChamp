"""Replay approved PDF embedded images into an independent visual index."""

from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.db.source_models import (
    SourceDecision,
    SourceProcessing,
    SourceRevision,
    SourceSegment,
    SourceVisual,
    SourceVisualIndex,
)
from app.infrastructure.ingestion.pdf_images import extract_pdf_images
from app.infrastructure.ingestion.pdf_text import ExtractionError
from app.infrastructure.ingestion.storage import PrivateOriginalStore
from app.infrastructure.ingestion.visual_storage import PrivateVisualStore
from app.infrastructure.vector.visual_vectors import MODEL_ID, QdrantVisualIndex


class ApprovedVisualIndexer:
    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        index: QdrantVisualIndex,
        originals: PrivateOriginalStore,
        visuals: PrivateVisualStore,
    ) -> None:
        self.factory = factory
        self.index = index
        self.originals = originals
        self.visuals = visuals
        self._audit_cursor: UUID | None = None

    async def index_one(self) -> UUID | None:
        if not await self.index.exists():
            async with self.factory.begin() as session:
                await session.execute(delete(SourceVisualIndex))
        await self.index.ensure()
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
        async with self.factory() as session:
            revision = await session.scalar(
                select(SourceRevision)
                .join(SourceProcessing, SourceProcessing.revision_id == SourceRevision.id)
                .join(SourceDecision, SourceDecision.revision_id == SourceRevision.id)
                .outerjoin(SourceVisualIndex, SourceVisualIndex.revision_id == SourceRevision.id)
                .where(
                    SourceProcessing.state == "review_pending",
                    SourceRevision.media_type == "application/pdf",
                    SourceDecision.event_id == latest,
                    SourceDecision.kind == "approve",
                    SourceDecision.user_text.is_(True),
                    SourceDecision.original_file.is_(True),
                    SourceDecision.sensitivity_cleared.is_(True),
                    ~excluded,
                    (SourceVisualIndex.revision_id.is_(None))
                    | (SourceVisualIndex.model_id != MODEL_ID),
                )
                .order_by(SourceRevision.captured_at)
                .limit(1)
            )
            if revision is None:
                return None
            old_ids = (
                await session.scalars(
                    select(SourceVisual.id).where(SourceVisual.revision_id == revision.id)
                )
            ).all()
            try:
                with self.originals.open_original(revision.storage_key) as stream:
                    images = extract_pdf_images(stream.read())
            except (OSError, ExtractionError):
                # The source may become readable after an operational repair.
                return None
        await self.index.delete(list(old_ids))
        entries: list[SourceVisual] = []
        points: list[tuple[UUID, UUID, str]] = []
        for image in images:
            key, digest = self.visuals.put(revision.id, image.png)
            point_id = uuid5(NAMESPACE_URL, f"{revision.id}:{image.page}:{image.ordinal}")
            entries.append(
                SourceVisual(
                    id=point_id,
                    revision_id=revision.id,
                    page=image.page,
                    ordinal=image.ordinal,
                    sha256=digest,
                    storage_key=key,
                )
            )
            points.append((point_id, revision.id, self.visuals.path(key)))
        await self.index.upsert(points)
        async with self.factory.begin() as session:
            await session.execute(
                delete(SourceVisual).where(SourceVisual.revision_id == revision.id)
            )
            session.add_all(entries)
            marker = await session.get(SourceVisualIndex, revision.id)
            if marker is None:
                session.add(SourceVisualIndex(revision_id=revision.id, model_id=MODEL_ID))
            else:
                marker.model_id = MODEL_ID
        return revision.id

    async def remove_revoked_one(self) -> UUID | None:
        latest = (
            select(func.max(SourceDecision.event_id))
            .where(SourceDecision.revision_id == SourceVisualIndex.revision_id)
            .correlate(SourceVisualIndex)
            .scalar_subquery()
        )
        async with self.factory() as session:
            revision_id = await session.scalar(
                select(SourceVisualIndex.revision_id)
                .join(SourceDecision, SourceDecision.revision_id == SourceVisualIndex.revision_id)
                .where(SourceDecision.event_id == latest, SourceDecision.kind == "revoke")
                .limit(1)
            )
            if revision_id is None:
                return None
            ids = (
                await session.scalars(
                    select(SourceVisual.id).where(SourceVisual.revision_id == revision_id)
                )
            ).all()
        await self.index.delete(list(ids))
        async with self.factory.begin() as session:
            marker = await session.get(SourceVisualIndex, revision_id)
            if marker is not None:
                await session.delete(marker)
        return revision_id

    async def audit_one(self) -> UUID | None:
        latest = (
            select(func.max(SourceDecision.event_id))
            .where(SourceDecision.revision_id == SourceVisualIndex.revision_id)
            .correlate(SourceVisualIndex)
            .scalar_subquery()
        )
        async with self.factory() as session:
            statement = (
                select(SourceVisualIndex.revision_id)
                .join(SourceDecision, SourceDecision.revision_id == SourceVisualIndex.revision_id)
                .where(
                    SourceVisualIndex.model_id == MODEL_ID,
                    SourceDecision.event_id == latest,
                    SourceDecision.kind == "approve",
                )
                .order_by(SourceVisualIndex.revision_id)
                .limit(1)
            )
            revision_id = None
            if self._audit_cursor is not None:
                revision_id = await session.scalar(
                    statement.where(SourceVisualIndex.revision_id > self._audit_cursor)
                )
            if revision_id is None:
                revision_id = await session.scalar(statement)
            if revision_id is None:
                self._audit_cursor = None
                return None
            ids = list(
                (
                    await session.scalars(
                        select(SourceVisual.id).where(SourceVisual.revision_id == revision_id)
                    )
                ).all()
            )
        self._audit_cursor = revision_id
        if await self.index.has_points(revision_id, ids):
            return None
        async with self.factory.begin() as session:
            marker = await session.get(SourceVisualIndex, revision_id)
            if marker is not None:
                await session.delete(marker)
        return revision_id
