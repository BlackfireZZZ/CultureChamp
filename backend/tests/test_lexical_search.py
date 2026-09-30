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
    SourceVectorIndex,
)
from app.infrastructure.db.source_repository import SourceRepository
from app.infrastructure.db.vector_search import SqlGovernedVectorSearch
from app.infrastructure.vector.indexing import ApprovedTextIndexer
from app.infrastructure.vector.text_vectors import (
    DIMENSIONS,
    LocalTextEmbedder,
    QdrantTextIndex,
    VectorUnavailable,
)


class ConstantEmbedder:
    async def query(self, text):
        return [1.0] + [0.0] * (DIMENSIONS - 1)

    async def passages(self, texts):
        return [[1.0] + [0.0] * (DIMENSIONS - 1) for _ in texts]


def test_search_terms_are_bounded_and_deterministic() -> None:
    assert search_terms("alpha ALPHA beta! x") == ("alpha", "beta")
    assert len(search_terms(" ".join(f"term{i}" for i in range(100)))) == 24


def test_lexical_search_filters_current_decision_before_ranking() -> None:
    url = os.getenv("CORPUS_TEST_DATABASE_URL")
    if url is None:
        pytest.skip("set CORPUS_TEST_DATABASE_URL for PostgreSQL integration")
    asyncio.run(_check_search(url))


def test_vector_search_rechecks_rights_after_candidate_ranking() -> None:
    url = os.getenv("CORPUS_TEST_DATABASE_URL")
    vector_url = os.getenv("CORPUS_TEST_VECTOR_URL")
    if url is None or vector_url is None:
        pytest.skip("set CORPUS_TEST_DATABASE_URL and CORPUS_TEST_VECTOR_URL")
    asyncio.run(_check_search(url, vector_url))


def test_multilingual_vector_paraphrase_ranks_relevant_passage_first() -> None:
    vector_url = os.getenv("CORPUS_TEST_VECTOR_URL")
    if vector_url is None:
        pytest.skip("set CORPUS_TEST_VECTOR_URL for live vector integration")

    async def check() -> None:
        gift_id, concert_id = uuid4(), uuid4()
        index = QdrantTextIndex(vector_url, LocalTextEmbedder())
        try:
            await index.upsert(
                [
                    (gift_id, uuid4(), "В вымышленном образце подарок сделан из бересты."),
                    (
                        concert_id,
                        uuid4(),
                        "В вымышленном образце сцену концерта освещают прожекторы.",
                    ),
                ]
            )
            results = await index.query("Из чего изготовлен сувенир из коры берёзы?", 100)
            scores = dict(results)
            assert scores[gift_id] > scores[concert_id]
        finally:
            await index.delete([gift_id, concert_id])

    asyncio.run(check())


def test_missing_vector_collection_fails_closed() -> None:
    vector_url = os.getenv("CORPUS_TEST_VECTOR_URL")
    if vector_url is None:
        pytest.skip("set CORPUS_TEST_VECTOR_URL for live vector integration")

    async def check() -> None:
        index = QdrantTextIndex(
            vector_url, ConstantEmbedder(), collection=f"missing_probe_{uuid4().hex}"
        )
        assert not await index.collection_exists()
        with pytest.raises(VectorUnavailable, match="missing"):
            await index.query("synthetic probe", 1)
        assert not await index.collection_exists()

    asyncio.run(check())


async def _check_search(url: str, vector_url: str | None = None) -> None:
    engine = create_async_engine(url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    marker = f"probe{uuid4().hex}"
    revisions = {}
    segment_ids = {}
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
                segment = await repo.add_segment(
                    revision.id, ordinal=0, kind="prose", text=words, locator=Locator(page=1)
                )
                segment_ids[name] = segment.id
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
        if vector_url is None:
            search = SqlLexicalSearch(factory)
        else:
            index = QdrantTextIndex(vector_url, ConstantEmbedder())
            indexer = ApprovedTextIndexer(factory, index)
            assert {await indexer.index_one(), await indexer.index_one()} == {
                revisions["visible"],
                revisions["provider"],
            }
            assert await indexer.index_one() is None
            # Simulate stale points from a held and a revoked revision.
            await index.upsert(
                [(segment_ids[name], revisions[name], marker) for name in ("held", "revoked")]
            )
            search = SqlGovernedVectorSearch(factory, index)
        service = RetrievalService(search)
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
        if vector_url is not None:
            assert await indexer.remove_revoked_one() == revisions["visible"]
            assert await indexer.remove_revoked_one() is None
    finally:
        if vector_url is not None:
            await index.delete(list(segment_ids.values()))
        async with factory.begin() as session:
            revision_ids = list(revisions.values())
            for model in (
                SourceDecision, SourceTag, SourceSegment, SourceProcessing, SourceVectorIndex
            ):
                await session.execute(delete(model).where(model.revision_id.in_(revision_ids)))
            await session.execute(delete(SourceRevision).where(SourceRevision.id.in_(revision_ids)))
            await session.execute(delete(Source).where(Source.id.in_(source_ids)))
        await engine.dispose()
