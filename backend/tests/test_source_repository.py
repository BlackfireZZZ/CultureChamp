import asyncio
import os

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.sources import DecisionKind, Locator, RevisionDecision, RightsScopes
from app.infrastructure.db.source_models import SourceRevision, SourceTag
from app.infrastructure.db.source_repository import SourceRepository


def test_repository_round_trip_and_revocation() -> None:
    database_url = os.getenv("CORPUS_TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("set CORPUS_TEST_DATABASE_URL for PostgreSQL integration")

    async def run() -> None:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session, session.begin():
            repository = SourceRepository(session)
            source = await repository.add_source("https://example.org/article")
            revision = await repository.add_revision(
                source.id,
                sha256="a" * 64,
                byte_size=123,
                media_type="application/pdf",
                storage_key=f"test/{source.id}",
                title="A candidate source",
                language="ru",
            )
            retry = await repository.add_revision(
                source.id,
                sha256="a" * 64,
                byte_size=123,
                media_type="application/pdf",
                storage_key=f"test/{source.id}",
                title="A changed title on retry must not replace the snapshot",
            )
            assert retry.id == revision.id
            assert retry.title == "A candidate source"
            await repository.add_tag(revision.id, "region", "Primorye")
            segment = await repository.add_segment(
                revision.id,
                ordinal=0,
                kind="prose",
                text="A test passage",
                locator=Locator(page=2, section="Introduction"),
            )
            assert await repository.get_visible_citation(revision.id, segment.id) is None
            await repository.record_decision(
                RevisionDecision(
                    revision.id,
                    DecisionKind.APPROVE,
                    RightsScopes(user_text=True),
                    True,
                ),
                reviewer_id="test-reviewer",
                reason="integration check",
                evidence_url="https://example.org/review",
            )
            citation = await repository.get_visible_citation(revision.id, segment.id)
            assert citation is not None
            assert citation.revision_id == revision.id
            assert citation.locator == Locator(page=2, section="Introduction")
            stored = await session.get(SourceRevision, revision.id)
            assert stored is not None and stored.sha256 == "a" * 64
            tags = (
                await session.scalars(select(SourceTag).where(SourceTag.revision_id == revision.id))
            ).all()
            assert [(tag.kind, tag.value) for tag in tags] == [("region", "Primorye")]
            await repository.record_decision(
                RevisionDecision(revision.id, DecisionKind.REVOKE, RightsScopes(), False),
                reviewer_id="test-reviewer",
                reason="withdrawn",
                evidence_url="https://example.org/withdrawal",
            )
            assert await repository.get_visible_citation(revision.id, segment.id) is None
            await session.rollback()
        await engine.dispose()

    asyncio.run(run())
