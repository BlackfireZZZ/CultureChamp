"""PostgreSQL and private-storage adapter for governed material use cases."""

import hashlib
from typing import BinaryIO
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.source_management import (
    AdminRevisionData,
    AdminSourceData,
    ApprovalData,
    IntakeData,
    MaterialData,
    OriginalData,
    SegmentData,
    SourceConflict,
    SourceInputError,
    SourceNotFound,
    TagData,
)
from app.domain.sources import DecisionKind, RevisionDecision, RightsScopes
from app.infrastructure.db.source_models import (
    Source,
    SourceDecision,
    SourceProcessing,
    SourceRevision,
    SourceSegment,
    SourceTag,
)
from app.infrastructure.db.source_repository import SourceRepository
from app.infrastructure.ingestion.storage import IntakeError, PrivatePdfStore


class SqlSourceGateway:
    def __init__(self, factory: async_sessionmaker[AsyncSession], store: PrivatePdfStore) -> None:
        self.factory = factory
        self.store = store

    async def upload(
        self,
        *,
        origin_url: str,
        title: str,
        creator: str | None,
        rights_note: str | None,
        source_id: UUID | None,
        stream: BinaryIO,
        filename: str,
        media_type: str,
        tags: tuple[TagData, ...],
    ) -> IntakeData:
        async with self.factory.begin() as session:
            repo = SourceRepository(session)
            if source_id is None:
                source = await repo.add_source(origin_url)
            else:
                existing = await session.scalar(
                    select(Source).where(Source.id == source_id).with_for_update()
                )
                if existing is None or existing.origin_url != origin_url:
                    raise SourceNotFound
                source = existing
            try:
                stored = self.store.store(
                    source.id, stream, filename=filename, claimed_media_type=media_type
                )
            except IntakeError as exc:
                raise SourceInputError(str(exc)) from exc
            existing_revision = await session.scalar(
                select(SourceRevision.id).where(
                    SourceRevision.source_id == source.id,
                    SourceRevision.sha256 == stored.sha256,
                )
            )
            revision = await repo.add_revision(
                source.id,
                sha256=stored.sha256,
                byte_size=stored.byte_size,
                media_type="application/pdf",
                storage_key=stored.storage_key,
                title=title,
                creator=creator,
                rights_note=rights_note,
            )
            if existing_revision is None:
                for tag in tags:
                    await repo.add_tag(revision.id, tag.kind, tag.value)
            processing = await session.get(SourceProcessing, revision.id)
            if processing is None:
                processing = SourceProcessing(revision_id=revision.id, state="candidate")
                session.add(processing)
            await session.flush()
            return IntakeData(source.id, revision.id, processing.state)

    async def _material(self, session: AsyncSession, revision: SourceRevision) -> MaterialData:
        source = await session.get(Source, revision.source_id)
        if source is None:
            raise SourceNotFound
        segments = (
            await session.scalars(
                select(SourceSegment)
                .where(SourceSegment.revision_id == revision.id)
                .order_by(SourceSegment.ordinal)
            )
        ).all()
        latest = await session.scalar(
            select(SourceDecision)
            .where(SourceDecision.revision_id == revision.id)
            .order_by(SourceDecision.event_id.desc())
            .limit(1)
        )
        return MaterialData(
            revision_id=revision.id,
            title=revision.title,
            creator=revision.creator,
            origin_url=source.origin_url,
            rights_usage_note=revision.rights_note,
            media_type=revision.media_type,
            segments=tuple(SegmentData(s.id, s.page or 1, s.text) for s in segments),
            original_available=bool(
                latest
                and latest.kind == "approve"
                and latest.user_text
                and latest.original_file
                and latest.sensitivity_cleared
            ),
        )

    async def admin_detail(self, revision_id: UUID) -> AdminRevisionData:
        async with self.factory() as session:
            revision = await session.get(SourceRevision, revision_id)
            if revision is None:
                raise SourceNotFound
            processing = await session.get(SourceProcessing, revision_id)
            decision = await session.scalar(
                select(SourceDecision)
                .where(SourceDecision.revision_id == revision_id)
                .order_by(SourceDecision.event_id.desc())
                .limit(1)
            )
            tags = (
                await session.scalars(
                    select(SourceTag)
                    .where(SourceTag.revision_id == revision_id)
                    .order_by(SourceTag.kind, SourceTag.value)
                )
            ).all()
            return AdminRevisionData(
                material=await self._material(session, revision),
                source_id=revision.source_id,
                status=processing.state if processing else "candidate",
                error_code=processing.error_code if processing else None,
                decision=decision.kind if decision else None,
                sha256=revision.sha256,
                tags=tuple(TagData(tag.kind, tag.value) for tag in tags),
            )

    async def admin_list(
        self, *, status: str | None, decision: str | None, limit: int
    ) -> list[AdminSourceData]:
        async with self.factory() as session:
            latest_kind = (
                select(SourceDecision.kind)
                .where(SourceDecision.revision_id == SourceRevision.id)
                .order_by(SourceDecision.event_id.desc())
                .limit(1)
                .correlate(SourceRevision)
                .scalar_subquery()
            )
            query = (
                select(SourceRevision, Source, SourceProcessing)
                .join(Source, Source.id == SourceRevision.source_id)
                .join(SourceProcessing, SourceProcessing.revision_id == SourceRevision.id)
            )
            if status is not None:
                query = query.where(SourceProcessing.state == status)
            if decision == "none":
                query = query.where(latest_kind.is_(None))
            elif decision is not None:
                query = query.where(latest_kind == decision)
            rows = (
                await session.execute(
                    query.order_by(SourceRevision.captured_at.desc()).limit(limit)
                )
            ).all()
            result = []
            for revision, source, processing in rows:
                decision = await session.scalar(
                    select(SourceDecision.kind)
                    .where(SourceDecision.revision_id == revision.id)
                    .order_by(SourceDecision.event_id.desc())
                    .limit(1)
                )
                result.append(
                    AdminSourceData(
                        source.id,
                        revision.id,
                        revision.title,
                        source.origin_url,
                        processing.state,
                        decision,
                    )
                )
            return result

    async def approve(self, revision_id: UUID, reviewer_id: str, data: ApprovalData) -> None:
        async with self.factory.begin() as session:
            processing = await session.get(SourceProcessing, revision_id, with_for_update=True)
            if processing is None or processing.state != "review_pending":
                raise SourceConflict("Revision is not reviewable")
            latest = await session.scalar(
                select(SourceDecision)
                .where(SourceDecision.revision_id == revision_id)
                .order_by(SourceDecision.event_id.desc())
                .limit(1)
            )
            if latest is not None:
                raise SourceConflict("Revision already decided")
            await SourceRepository(session).record_decision(
                RevisionDecision(
                    revision_id,
                    DecisionKind.APPROVE,
                    RightsScopes(data.user_text, data.original_file, data.provider_transfer),
                    data.sensitivity_cleared,
                ),
                reviewer_id=reviewer_id,
                reason=data.reason,
                evidence_url=data.evidence_url,
            )

    async def revoke(self, revision_id: UUID, reviewer_id: str, reason: str) -> None:
        async with self.factory.begin() as session:
            processing = await session.get(SourceProcessing, revision_id, with_for_update=True)
            if processing is None:
                raise SourceNotFound
            latest = await session.scalar(
                select(SourceDecision)
                .where(SourceDecision.revision_id == revision_id)
                .order_by(SourceDecision.event_id.desc())
                .limit(1)
            )
            if latest is None or latest.kind != "approve":
                raise SourceConflict("Revision is not approved")
            await SourceRepository(session).record_decision(
                RevisionDecision(revision_id, DecisionKind.REVOKE, RightsScopes(), False),
                reviewer_id=reviewer_id,
                reason=reason,
                evidence_url=latest.evidence_url,
            )

    async def retry(self, revision_id: UUID) -> None:
        async with self.factory.begin() as session:
            record = await session.get(SourceProcessing, revision_id, with_for_update=True)
            if record is None:
                raise SourceNotFound
            if record.state != "failed":
                raise SourceConflict("Only failed processing can be retried")
            record.state = "candidate"
            record.error_code = None

    @staticmethod
    def _visible_query():
        latest_event = (
            select(func.max(SourceDecision.event_id))
            .where(SourceDecision.revision_id == SourceRevision.id)
            .correlate(SourceRevision)
            .scalar_subquery()
        )
        return (
            select(SourceRevision)
            .join(SourceProcessing, SourceProcessing.revision_id == SourceRevision.id)
            .join(SourceDecision, SourceDecision.revision_id == SourceRevision.id)
            .where(
                SourceProcessing.state == "review_pending",
                SourceDecision.event_id == latest_event,
                SourceDecision.kind == "approve",
                SourceDecision.user_text.is_(True),
                SourceDecision.sensitivity_cleared.is_(True),
            )
        )

    async def visible_list(self) -> list[MaterialData]:
        async with self.factory() as session:
            revisions = (
                await session.scalars(self._visible_query().order_by(SourceRevision.captured_at))
            ).all()
            return [await self._material(session, revision) for revision in revisions]

    async def visible_detail(self, revision_id: UUID) -> MaterialData:
        async with self.factory() as session:
            revision = await session.scalar(
                self._visible_query().where(SourceRevision.id == revision_id)
            )
            if revision is None:
                raise SourceNotFound
            return await self._material(session, revision)

    async def visible_original(self, revision_id: UUID) -> OriginalData:
        async with self.factory() as session:
            revision = await session.scalar(
                self._visible_query().where(
                    SourceRevision.id == revision_id,
                    SourceDecision.original_file.is_(True),
                )
            )
            if revision is None:
                raise SourceNotFound
            try:
                with self.store.open_original(revision.storage_key) as stream:
                    content = stream.read()
            except (OSError, IntakeError) as exc:
                raise SourceNotFound from exc
            if hashlib.sha256(content).hexdigest() != revision.sha256:
                raise SourceNotFound
            return OriginalData(content, f"source-{revision_id}.pdf")
