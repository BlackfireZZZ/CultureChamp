"""Database adapter for source identity and exact-revision visibility."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.sources import Citation, Locator, RevisionDecision
from app.infrastructure.db.source_models import (
    Source,
    SourceDecision,
    SourceRevision,
    SourceSegment,
    SourceTag,
)


class SourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_source(self, origin_url: str) -> Source:
        source = Source(origin_url=origin_url)
        self.session.add(source)
        await self.session.flush()
        return source

    async def add_revision(
        self,
        source_id: UUID,
        *,
        sha256: str,
        byte_size: int,
        media_type: str,
        storage_key: str,
        title: str,
        creator: str | None = None,
        language: str | None = None,
        period_note: str | None = None,
        rights_note: str | None = None,
    ) -> SourceRevision:
        revision = SourceRevision(
            source_id=source_id,
            sha256=sha256,
            byte_size=byte_size,
            media_type=media_type,
            storage_key=storage_key,
            title=title,
            creator=creator,
            language=language,
            period_note=period_note,
            rights_note=rights_note,
        )
        self.session.add(revision)
        await self.session.flush()
        return revision

    async def add_tag(self, revision_id: UUID, kind: str, value: str) -> SourceTag:
        tag = SourceTag(revision_id=revision_id, kind=kind, value=value)
        self.session.add(tag)
        await self.session.flush()
        return tag

    async def add_segment(
        self,
        revision_id: UUID,
        *,
        ordinal: int,
        kind: str,
        text: str,
        locator: Locator,
    ) -> SourceSegment:
        segment = SourceSegment(
            revision_id=revision_id,
            ordinal=ordinal,
            kind=kind,
            text=text,
            page=locator.page,
            section=locator.section,
            sheet=locator.sheet,
            table_name=locator.table,
            row_start=locator.row_start,
            row_end=locator.row_end,
            column_start=locator.column_start,
            column_end=locator.column_end,
        )
        self.session.add(segment)
        await self.session.flush()
        return segment

    async def record_decision(
        self,
        decision: RevisionDecision,
        *,
        reviewer_id: str,
        reason: str,
        evidence_url: str,
    ) -> SourceDecision:
        event = SourceDecision(
            revision_id=decision.revision_id,
            kind=decision.kind.value,
            reviewer_id=reviewer_id,
            reason=reason,
            evidence_url=evidence_url,
            user_text=decision.rights.user_text,
            original_file=decision.rights.original_file,
            provider_transfer=decision.rights.provider_transfer,
            sensitivity_cleared=decision.sensitivity_cleared,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def get_visible_citation(self, revision_id: UUID, segment_id: UUID) -> Citation | None:
        latest_event_id = (
            select(func.max(SourceDecision.event_id))
            .where(SourceDecision.revision_id == revision_id)
            .scalar_subquery()
        )
        query = (
            select(SourceSegment)
            .join(SourceDecision, SourceDecision.revision_id == SourceSegment.revision_id)
            .where(
                SourceSegment.revision_id == revision_id,
                SourceSegment.id == segment_id,
                SourceDecision.event_id == latest_event_id,
                SourceDecision.kind == "approve",
                SourceDecision.user_text.is_(True),
                SourceDecision.sensitivity_cleared.is_(True),
            )
        )
        segment = await self.session.scalar(query)
        if segment is None:
            return None
        return Citation(
            revision_id=revision_id,
            segment_id=segment_id,
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
        )
