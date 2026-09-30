"""Durable, retryable PDF extraction without publishing candidate text."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.db.source_models import SourceProcessing, SourceRevision, SourceSegment
from app.infrastructure.ingestion.isolated_pdf import extract_pdf_isolated
from app.infrastructure.ingestion.pdf_text import ExtractionError
from app.infrastructure.ingestion.storage import PrivatePdfStore


async def process_one(
    factory: async_sessionmaker[AsyncSession], store: PrivatePdfStore
) -> UUID | None:
    now = datetime.now(UTC)
    async with factory.begin() as session:
        record = await session.scalar(
            select(SourceProcessing)
            .where(
                or_(
                    SourceProcessing.state == "candidate",
                    (SourceProcessing.state == "processing") & (SourceProcessing.lease_until < now),
                )
            )
            .order_by(SourceProcessing.updated_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if record is None:
            return None
        revision_id = record.revision_id
        record.state = "processing"
        record.lease_until = now + timedelta(minutes=5)
        record.attempts += 1
        attempt = record.attempts
    try:
        async with factory() as session:
            revision = await session.get(SourceRevision, revision_id)
            if revision is None:
                raise ExtractionError("revision missing")
            with store.open_original(revision.storage_key) as stream:
                pages = extract_pdf_isolated(stream.read())
    except (ExtractionError, OSError, ValueError):
        async with factory.begin() as session:
            record = await session.get(SourceProcessing, revision_id, with_for_update=True)
            if record is not None and record.state == "processing" and record.attempts == attempt:
                record.state = "failed"
                record.error_code = "pdf_extraction_failed"
                record.lease_until = None
        return revision_id
    async with factory.begin() as session:
        record = await session.get(SourceProcessing, revision_id, with_for_update=True)
        if record is None or record.state != "processing" or record.attempts != attempt:
            return revision_id
        await session.execute(delete(SourceSegment).where(SourceSegment.revision_id == revision_id))
        for page in pages:
            session.add(
                SourceSegment(
                    revision_id=revision_id,
                    ordinal=page.ordinal,
                    kind="prose",
                    text=page.text,
                    page=page.locator.page,
                )
            )
        record.state = "review_pending"
        record.error_code = None
        record.lease_until = None
    return revision_id


async def run_worker(factory: async_sessionmaker[AsyncSession], root: Path) -> None:
    import asyncio

    store = PrivatePdfStore(root)
    while True:
        if await process_one(factory, store) is None:
            await asyncio.sleep(2)
