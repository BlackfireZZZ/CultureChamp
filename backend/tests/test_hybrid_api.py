"""Opt-in SQL/Qdrant API contracts; synthetic models never load model weights."""

import asyncio
import os
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.application.access import Role
from app.application.identity import IdentityService
from app.domain.sources import DecisionKind, Locator, RevisionDecision, RightsScopes
from app.infrastructure.db.hybrid_search import SqlGovernedHybridSearch
from app.infrastructure.db.identity_models import Account, LoginSession
from app.infrastructure.db.identity_store import SqlIdentityStore
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
from app.infrastructure.passwords import Argon2PasswordCodec
from app.infrastructure.vector.local_retrieval import RussianBM25
from app.infrastructure.vector.text_vectors import (
    DIMENSIONS,
    MODEL_ID,
    QdrantTextIndex,
    VectorUnavailable,
)
from app.main import create_app


class SyntheticEmbedder:
    async def query(self, text):
        return [1.0] + [0.0] * (DIMENSIONS - 1)

    async def passages(self, texts):
        return [
            ([0.8, 0.6] if "берестяной" in text else [1.0, 0.0]) + [0.0] * (DIMENSIONS - 2)
            for text in texts
        ]


class SyntheticReranker:
    def __init__(self):
        self.seen = []
        self.before_return = None
        self.fail = False

    async def rerank(self, query, passages):
        self.seen = list(passages)
        if self.fail:
            raise VectorUnavailable("Synthetic unavailable reranker")
        if self.before_return is not None:
            await self.before_return()
        return [10.0 if "берестяной" in text else 1.0 for text in passages]


@pytest.fixture
def hybrid_corpus():
    url = os.getenv("CORPUS_TEST_DATABASE_URL")
    vector_url = os.getenv("CORPUS_TEST_VECTOR_URL")
    if not url or not vector_url:
        pytest.skip("set CORPUS_TEST_DATABASE_URL and CORPUS_TEST_VECTOR_URL")
    engine = create_async_engine(url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    marker = uuid4().hex
    region = f"Synthetic {marker}"
    index = QdrantTextIndex(vector_url, SyntheticEmbedder(), collection=f"hybrid_api_{marker}")
    reranker = SyntheticReranker()
    revisions, sources, accounts, segments, rows = {}, [], [], {}, []
    identity = SqlIdentityStore(factory)
    codec = Argon2PasswordCodec()
    password = "synthetic-retrieval-password"
    usernames = {role: f"hybrid-{role.value}-{marker[:12]}" for role in (Role.USER, Role.ADMIN)}

    async def seed():
        for role, username in usernames.items():
            account = await identity.create_account(username, await codec.hash(password), role)
            accounts.append(account.id)
        async with factory.begin() as session:
            repo = SourceRepository(session)
            for name in ("visible", "provider", "held", "revoked", "pending"):
                source = await repo.add_source(f"https://example.invalid/{marker}/{name}")
                sources.append(source.id)
                revision = await repo.add_revision(
                    source.id,
                    sha256=uuid4().hex * 2,
                    byte_size=100,
                    media_type="application/pdf",
                    storage_key=f"{marker}/{name}.pdf",
                    title=f"Synthetic {name}",
                    rights_note="Self-authored synthetic fixture",
                )
                revisions[name] = revision.id
                session.add(SourceProcessing(revision_id=revision.id, state="review_pending"))
                await repo.add_tag(
                    revision.id, "region", region if name != "pending" else region + " pending"
                )
                await repo.add_tag(revision.id, "people", name)
                if name != "held":
                    await repo.record_decision(
                        RevisionDecision(
                            revision.id,
                            DecisionKind.APPROVE,
                            RightsScopes(user_text=True, provider_transfer=name == "provider"),
                            True,
                        ),
                        reviewer_id="synthetic",
                        reason="Synthetic approval",
                        evidence_url="https://example.invalid/rights",
                    )
                if name == "revoked":
                    await repo.record_decision(
                        RevisionDecision(revision.id, DecisionKind.REVOKE, RightsScopes(), False),
                        reviewer_id="synthetic",
                        reason="Synthetic revocation",
                        evidence_url="https://example.invalid/rights",
                    )
                if name != "pending":
                    session.add(SourceVectorIndex(revision_id=revision.id, model_id=MODEL_ID))
                count = 65 if name == "visible" else 60 if name in ("held", "revoked") else 1
                for ordinal in range(count):
                    text = (
                        "берестяной сосуд хранит воду"
                        if name == "visible" and ordinal == 64
                        else f"synthetic noise {name} {ordinal}"
                    )
                    segment = await repo.add_segment(
                        revision.id,
                        ordinal=ordinal,
                        kind="prose",
                        text=text,
                        locator=Locator(page=ordinal + 1, section=f"span:{ordinal}:synthetic"),
                    )
                    segments[name, ordinal] = segment.id
                    rows.append((segment.id, revision.id, text))
                if name == "visible":
                    for ordinal in range(65, 125):
                        segment = await repo.add_segment(
                            revision.id,
                            ordinal=ordinal,
                            kind="prose",
                            text="excluded stale point",
                            locator=Locator(page=ordinal + 1),
                        )
                        segment.included = False
                        rows.append((segment.id, revision.id, segment.text))
        await index.upsert(rows)

    async def cleanup():
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                result = await client.delete(f"{vector_url}/collections/{index.collection}")
                if result.status_code != 404:
                    result.raise_for_status()
        finally:
            async with factory.begin() as session:
                ids = list(revisions.values())
                for model in (
                    SourceDecision,
                    SourceTag,
                    SourceSegment,
                    SourceProcessing,
                    SourceVectorIndex,
                ):
                    await session.execute(delete(model).where(model.revision_id.in_(ids)))
                await session.execute(delete(SourceRevision).where(SourceRevision.id.in_(ids)))
                await session.execute(delete(Source).where(Source.id.in_(sources)))
                await session.execute(
                    delete(LoginSession).where(LoginSession.account_id.in_(accounts))
                )
                await session.execute(delete(Account).where(Account.id.in_(accounts)))
            await engine.dispose()

    try:
        asyncio.run(seed())
        app = create_app()
        app.state.source_session_factory = factory
        app.state.session_store = identity
        app.state.identity_service = IdentityService(identity, codec, codec.dummy_hash)
        app.state.vector_index = index
        app.state.retrieval_reranker = reranker
        app.state.retrieval_lexical = RussianBM25()
        with TestClient(app) as client:
            yield client, factory, index, reranker, revisions, segments, region, usernames, password
    finally:
        asyncio.run(cleanup())


def _login(client, usernames, password, role=Role.USER):
    result = client.post(
        "/api/v1/auth/login",
        json={"username": usernames[role], "password": password},
        headers={"origin": "http://testserver"},
    )
    assert result.status_code == 200, result.text


def test_hybrid_api_retrieves_lexical_dense_tail_and_validates_access(hybrid_corpus):
    client, factory, index, reranker, revisions, segments, region, usernames, password = (
        hybrid_corpus
    )
    path = "/api/v1/materials/search"
    assert client.get(path, params={"q": "берестяной"}).status_code == 401
    _login(client, usernames, password, Role.ADMIN)
    assert client.get(path, params={"q": "берестяной"}).status_code == 403
    _login(client, usernames, password)
    for params in ({"q": " "}, {"q": "сосуд", "limit": 21}, {"q": "сосуд", "region": " "}):
        assert client.get(path, params=params).status_code == 422
    dense = asyncio.run(index.query("берестяной", 50, allowed_revision_ids=[revisions["visible"]]))
    assert segments["visible", 64] not in dict(dense)
    # The low-score included point survives even with 180 higher-scoring stale
    # held/revoked/excluded points in the same Qdrant collection.
    isolated = asyncio.run(
        index.query(
            "берестяной",
            1,
            allowed_revision_ids=[revisions["visible"]],
            allowed_segment_ids=[segments["visible", 64]],
        )
    )
    assert [sid for sid, _ in isolated] == [segments["visible", 64]]
    result = client.get(path, params={"q": "берестяной", "region": region, "limit": 10})
    assert result.status_code == 200, result.text
    assert result.headers["cache-control"] == "no-store"
    found = result.json()
    assert found[0]["segment_id"] == str(segments["visible", 64])
    assert found[0]["locator"]["page"] == 65
    assert found[0]["locator"]["section"] == "span:64:synthetic"
    assert found[0]["text"] == "берестяной сосуд хранит воду"
    assert found[0]["score"] == 10.0
    assert all(
        item["revision_id"] in {str(revisions["visible"]), str(revisions["provider"])}
        for item in found
    )
    assert "excluded stale point" not in reranker.seen
    assert not any("held" in text or "revoked" in text for text in reranker.seen)
    filtered = client.get(path, params={"q": "сосуд", "region": region, "people": "provider"})
    assert filtered.status_code == 200
    assert [item["revision_id"] for item in filtered.json()] == [str(revisions["provider"])]
    assert len(reranker.seen) == 1
    search = SqlGovernedHybridSearch(factory, index, reranker)
    provider = asyncio.run(
        search.search("сосуд", limit=10, region=region, people=None, for_provider=True)
    )
    assert [item.revision_id for item in provider] == [revisions["provider"]]
    assert len(reranker.seen) == 1
    pending = client.get(path, params={"q": "сосуд", "region": region + " pending"})
    assert pending.status_code == 503
    assert client.get(path, params={"q": "сосуд", "region": "absent-" + region}).json() == []
    reranker.fail = True
    assert client.get(path, params={"q": "берестяной", "region": region}).status_code == 503


@pytest.mark.parametrize("mutation", ["revoke", "exclude"])
def test_hybrid_api_rechecks_governance_after_reranking(hybrid_corpus, mutation):
    client, factory, _, reranker, revisions, segments, region, usernames, password = hybrid_corpus
    _login(client, usernames, password)

    async def change_while_reranking():
        async with factory.begin() as session:
            if mutation == "exclude":
                await session.execute(
                    update(SourceSegment)
                    .where(SourceSegment.id == segments["visible", 64])
                    .values(included=False)
                )
            else:
                await SourceRepository(session).record_decision(
                    RevisionDecision(
                        revisions["visible"], DecisionKind.REVOKE, RightsScopes(), False
                    ),
                    reviewer_id="synthetic",
                    reason="Synthetic concurrent revocation",
                    evidence_url="https://example.invalid/rights",
                )

    reranker.before_return = change_while_reranking
    result = client.get("/api/v1/materials/search", params={"q": "берестяной", "region": region})
    assert result.status_code == 200, result.text
    assert "берестяной сосуд хранит воду" in reranker.seen
    assert str(segments["visible", 64]) not in {item["segment_id"] for item in result.json()}
    if mutation == "revoke":
        assert all(item["revision_id"] != str(revisions["visible"]) for item in result.json())
