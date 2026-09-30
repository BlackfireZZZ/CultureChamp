import asyncio
import os
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.application.access import AccessDenied, Actor, Role
from app.application.retrieval import RetrievalService
from app.domain.sources import DecisionKind, Locator, RevisionDecision, RightsScopes
from app.infrastructure.db.lexical_search import SqlLexicalSearch, search_terms
from app.infrastructure.db.source_models import (
    Source,
    SourceDecision,
    SourceProcessing,
    SourceRevision,
    SourceSegment,
    SourceTag,
)
from app.infrastructure.db.source_repository import SourceRepository


def test_search_terms_are_bounded_and_deterministic() -> None:
    assert search_terms("alpha ALPHA beta! x") == ("alpha", "beta")
    assert len(search_terms(" ".join(f"term{i}" for i in range(100)))) == 24


def test_lexical_search_filters_current_decision_before_ranking() -> None:
    url = os.getenv("CORPUS_TEST_DATABASE_URL")
    if url is None:
        pytest.skip("set CORPUS_TEST_DATABASE_URL for PostgreSQL integration")
    asyncio.run(_check_search(url))


async def _check_search(url: str) -> None:
    engine = create_async_engine(url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    marker = f"probe{uuid4().hex}"
    revisions = {}
    source_ids = []
    try:
        async with factory.begin() as session:
            repo = SourceRepository(session)
            for name, words, transfer in (
                ("visible", marker, False),
                ("provider", f"{marker} provider", True),
                ("held", f"{marker} " * 20, False),
                ("revoked", f"{marker} " * 20, False),
            ):
                source = await repo.add_source(f"https://example.invalid/synthetic/{name}/{marker}")
                source_ids.append(source.id)
                revision = await repo.add_revision(
                    source.id,
                    sha256=uuid4().hex * 2,
                    byte_size=100,
                    media_type="application/pdf",
                    storage_key=f"{source.id}/{uuid4().hex * 2}.pdf",
                    title=f"Synthetic {name}",
                    rights_note="Self-authored synthetic search check",
                )
                revisions[name] = revision.id
                await repo.add_segment(
                    revision.id, ordinal=0, kind="prose", text=words, locator=Locator(page=1)
                )
                await repo.add_tag(revision.id, "region", "Synthetic region")
                session.add(SourceProcessing(revision_id=revision.id, state="review_pending"))
                if name != "held":
                    await repo.record_decision(
                        RevisionDecision(
                            revision.id,
                            DecisionKind.APPROVE,
                            RightsScopes(user_text=True, provider_transfer=transfer),
                            True,
                        ),
                        reviewer_id="synthetic-test",
                        reason="Self-authored synthetic fixture",
                        evidence_url="https://example.invalid/synthetic/rights",
                    )
                    if name == "revoked":
                        await repo.record_decision(
                            RevisionDecision(
                                revision.id, DecisionKind.REVOKE, RightsScopes(), False
                            ),
                            reviewer_id="synthetic-test",
                            reason="Synthetic revocation check",
                            evidence_url="https://example.invalid/synthetic/rights",
                        )
        service = RetrievalService(SqlLexicalSearch(factory))
        user = Actor("synthetic-user", Role.USER)
        found = await service.search(user, marker)
        assert await service.search(user, marker) == found
        assert {item.revision_id for item in found} == {
            revisions["visible"], revisions["provider"]
        }
        assert all(item.locator.page == 1 and item.segment_id for item in found)
        provider = await service.search(user, marker, for_provider=True)
        assert [item.revision_id for item in provider] == [revisions["provider"]]
        assert await service.search(user, marker, region="Missing region") == ()
        assert len(await service.search(user, marker, region="Synthetic region")) == 2
        with pytest.raises(AccessDenied):
            await service.search(Actor("synthetic-admin", Role.ADMIN), marker)
        async with factory.begin() as session:
            await SourceRepository(session).record_decision(
                RevisionDecision(
                    revisions["visible"], DecisionKind.REVOKE, RightsScopes(), False
                ),
                reviewer_id="synthetic-test",
                reason="Synthetic late revocation check",
                evidence_url="https://example.invalid/synthetic/rights",
            )
        assert [item.revision_id for item in await service.search(user, marker)] == [
            revisions["provider"]
        ]
    finally:
        async with factory.begin() as session:
            revision_ids = list(revisions.values())
            for model in (SourceDecision, SourceTag, SourceSegment, SourceProcessing):
                await session.execute(delete(model).where(model.revision_id.in_(revision_ids)))
            await session.execute(delete(SourceRevision).where(SourceRevision.id.in_(revision_ids)))
            await session.execute(delete(Source).where(Source.id.in_(source_ids)))
        await engine.dispose()
