"""Durable, retryable PDF extraction without publishing candidate text."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import monotonic
from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.infrastructure.db.chat_store import SqlChatStore
from app.infrastructure.db.model_quota import SqlModelQuota
from app.infrastructure.db.source_models import SourceProcessing, SourceRevision, SourceSegment
from app.infrastructure.ingestion.chunking import chunk_text
from app.infrastructure.ingestion.isolated_pdf import extract_pdf_isolated
from app.infrastructure.ingestion.pdf_text import ExtractionError
from app.infrastructure.ingestion.storage import PrivatePdfStore
from app.infrastructure.vector.indexing import ApprovedTextIndexer
from app.infrastructure.vector.text_vectors import (
    LocalTextEmbedder,
    QdrantTextIndex,
    VectorUnavailable,
)


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
        ordinal = 0
        for page in pages:
            for excerpt in chunk_text(page.text):
                session.add(
                    SourceSegment(
                        revision_id=revision_id,
                        ordinal=ordinal,
                        kind="prose",
                        text=excerpt,
                        page=page.locator.page,
                    )
                )
                ordinal += 1
        record.state = "review_pending"
        record.error_code = None
        record.lease_until = None
    return revision_id


async def run_worker(factory: async_sessionmaker[AsyncSession], root: Path) -> None:
    import asyncio

    store = PrivatePdfStore(root)
    indexer = ApprovedTextIndexer(
        factory, QdrantTextIndex(settings.vector_url, LocalTextEmbedder())
    )
    next_purge = 0.0
    while True:
        if monotonic() >= next_purge:
            await SqlChatStore(factory).purge_expired()
            await SqlModelQuota(factory).purge_old()
            next_purge = monotonic() + 3600
        processed = await process_one(factory, store)
        audited = None
        try:
            indexed = await indexer.index_one()
            removed = await indexer.remove_revoked_one()
            if processed is None and indexed is None and removed is None:
                audited = await indexer.audit_one()
        except VectorUnavailable:
            indexed = removed = None
        if processed is None and indexed is None and removed is None and audited is None:
            await asyncio.sleep(2)
