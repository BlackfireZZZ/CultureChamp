import asyncio
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.application.access import Role
from app.application.identity import IdentityService
from app.domain.sources import DecisionKind, Locator, RevisionDecision, RightsScopes
from app.infrastructure.db.chat_models import ChatConversation
from app.infrastructure.db.chat_store import SqlChatStore
from app.infrastructure.db.identity_store import SqlIdentityStore
from app.infrastructure.db.source_models import (
    Source,
    SourceDecision,
    SourceProcessing,
    SourceRevision,
    SourceSegment,
    SourceVectorIndex,
)
from app.infrastructure.db.source_repository import SourceRepository
from app.infrastructure.ingestion.storage import PrivateOriginalStore
from app.infrastructure.model.gateway import ModelFailure, ModelRequest, ModelResult
from app.infrastructure.model.http import HttpModelProvider
from app.infrastructure.passwords import Argon2PasswordCodec
from app.infrastructure.vector.indexing import ApprovedTextIndexer
from app.infrastructure.vector.text_vectors import DIMENSIONS, QdrantTextIndex
from app.main import create_app

PASSWORD = "synthetic-chat-test-password"


class BrokenProvider:
    async def generate(self, request: ModelRequest) -> ModelResult:
        raise ModelFailure("provider_unavailable")


class ConstantEmbedder:
    async def query(self, text):
        return [1.0] + [0.0] * (DIMENSIONS - 1)

    async def passages(self, texts):
        return [[1.0] + [0.0] * (DIMENSIONS - 1) for _ in texts]


def test_persisted_chat_ownership_retry_citation_revocation_and_purge(tmp_path: Path) -> None:
    url = os.getenv("CORPUS_TEST_DATABASE_URL")
    if url is None or os.getenv("CORPUS_TEST_VECTOR_URL") is None:
        pytest.skip("set CORPUS_TEST_DATABASE_URL and CORPUS_TEST_VECTOR_URL")
    asyncio.run(_check_chat(url, tmp_path))


async def _seed_source(
    factory: async_sessionmaker, marker: str, *, provider_transfer: bool = False,
    approve: bool = True,
) -> tuple[UUID, UUID]:
    async with factory.begin() as session:
        repo = SourceRepository(session)
        source = await repo.add_source(f"https://example.invalid/synthetic-chat/{marker}")
        revision = await repo.add_revision(
            source.id,
            sha256=uuid4().hex * 2,
            byte_size=100,
            media_type="application/pdf",
            storage_key=f"{source.id}/{uuid4().hex * 2}.pdf",
            title=f"Self-authored synthetic chat fixture {marker}",
            rights_note="Self-authored synthetic content; technical test only",
        )
        await repo.add_segment(
            revision.id,
            ordinal=0,
            kind="prose",
            text=f"Synthetic marker {marker} has count seven.",
            locator=Locator(page=1),
        )
        session.add(SourceProcessing(revision_id=revision.id, state="review_pending"))
        if approve:
            await repo.record_decision(
                RevisionDecision(
                    revision.id,
                    DecisionKind.APPROVE,
                    RightsScopes(
                        user_text=True, original_file=False,
                        provider_transfer=provider_transfer,
                    ),
                    True,
                ),
                reviewer_id="synthetic-test",
                reason="Self-authored synthetic fixture approved for mechanics test",
                evidence_url="https://example.invalid/synthetic-chat/rights",
            )
        return source.id, revision.id


async def _check_chat(url: str, tmp_path: Path) -> None:
    engine = create_async_engine(url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    identity_store = SqlIdentityStore(factory)
    codec = Argon2PasswordCodec()
    app = create_app()
    default_provider = app.state.model_provider
    app.state.session_store = identity_store
    app.state.identity_service = IdentityService(identity_store, codec, codec.dummy_hash)
    app.state.source_session_factory = factory
    app.state.source_store = PrivateOriginalStore(tmp_path / "private")
    index = QdrantTextIndex(os.environ["CORPUS_TEST_VECTOR_URL"], ConstantEmbedder())
    app.state.vector_index = index
    marker = f"chatprobe{uuid4().hex}"
    names = [
        f"chat-a-{uuid4().hex[:12]}",
        f"chat-b-{uuid4().hex[:12]}",
        f"chat-admin-{uuid4().hex[:12]}",
    ]
    seeded_sources: list[tuple[UUID, UUID]] = []
    chat_id: str | None = None

    async def seed_accounts() -> None:
        for name, role in zip(names, (Role.USER, Role.USER, Role.ADMIN), strict=True):
            await identity_store.create_account(name, await codec.hash(PASSWORD), role)

    await seed_accounts()
    origin = "http://testserver"
    try:
        with (
            TestClient(app, base_url=origin) as owner,
            TestClient(app, base_url=origin) as other,
            TestClient(app, base_url=origin) as admin,
        ):

            def login(client: TestClient, name: str) -> dict[str, str]:
                result = client.post(
                    "/api/v1/auth/login",
                    json={"username": name, "password": PASSWORD},
                    headers={"origin": origin},
                )
                assert result.status_code == 200
                return {"origin": origin, "x-csrf-token": result.json()["csrf_token"]}

            owner_headers, other_headers, admin_headers = (
                login(owner, names[0]),
                login(other, names[1]),
                login(admin, names[2]),
            )
            assert admin.post("/api/v1/chats", headers=admin_headers).status_code == 403
            created = owner.post("/api/v1/chats", headers=owner_headers)
            assert created.status_code == 201, created.text
            chat_id = created.json()["id"]
            assert owner.get("/api/v1/chats").headers["cache-control"] == "no-store"
            assert [row["id"] for row in owner.get("/api/v1/chats").json()] == [chat_id]
            assert other.get(f"/api/v1/chats/{chat_id}").status_code == 404
            assert (
                other.delete(f"/api/v1/chats/{chat_id}", headers=other_headers).status_code == 404
            )
            assert (
                owner.post(
                    f"/api/v1/chats/{chat_id}/messages",
                    headers=owner_headers,
                    json={"request_id": str(uuid4()), "text": "   "},
                ).status_code
                == 422
            )

            hidden_marker = f"unpublished{uuid4().hex}"
            hidden_source, hidden_revision = await _seed_source(
                factory, hidden_marker, approve=False
            )
            seeded_sources.append((hidden_source, hidden_revision))
            async with factory() as session:
                hidden_segment = await session.scalar(
                    select(SourceSegment).where(SourceSegment.revision_id == hidden_revision)
                )
            assert hidden_segment is not None
            await index.upsert([(hidden_segment.id, hidden_revision, hidden_segment.text)])
            admin_candidate = admin.get(f"/api/v1/admin/revisions/{hidden_revision}")
            assert admin_candidate.status_code == 200
            assert admin_candidate.json()["title"].endswith(hidden_marker)
            assert owner.get(f"/api/v1/materials/{hidden_revision}").status_code == 404
            assert owner.get(f"/api/v1/materials/{hidden_revision}/original").status_code == 404
            assert owner.get("/api/v1/materials", params={"q": hidden_marker}).json() == []

            no_evidence_id = str(uuid4())
            no_evidence = {"request_id": no_evidence_id, "text": hidden_marker}
            first = owner.post(
                f"/api/v1/chats/{chat_id}/messages", headers=owner_headers, json=no_evidence
            )
            assert first.status_code == 200, first.text
            assert first.json()["evidence_status"] == "insufficient"
            assert first.json()["citations"] == []
            assert hidden_marker not in first.json()["assistant_text"]
            repeated = owner.post(
                f"/api/v1/chats/{chat_id}/messages", headers=owner_headers, json=no_evidence
            )
            assert repeated.status_code == 200
            assert repeated.json() == first.json()
            assert (
                owner.post(
                    f"/api/v1/chats/{chat_id}/messages",
                    headers=owner_headers,
                    json={"request_id": no_evidence_id, "text": "different"},
                ).status_code
                == 409
            )
            source_id, revision_id = await _seed_source(factory, marker)
            seeded_sources.append((source_id, revision_id))
            async with factory() as session:
                segments = (
                    await session.scalars(
                        select(SourceSegment).where(SourceSegment.revision_id == revision_id)
                    )
                ).all()
            assert await ApprovedTextIndexer(factory, index).index_one() == revision_id
            external_calls: list[httpx.Request] = []

            def external_handler(request: httpx.Request) -> httpx.Response:
                external_calls.append(request)
                return httpx.Response(200, json={})

            async with httpx.AsyncClient(transport=httpx.MockTransport(external_handler)) as client:
                app.state.model_provider = HttpModelProvider(
                    endpoint="https://approved.example/v1/chat/completions",
                    model="pilot-model", api_key="synthetic-key", policy_approved=True,
                    client=client,
                )
                held_from_provider = owner.post(
                    f"/api/v1/chats/{chat_id}/messages", headers=owner_headers,
                    json={"request_id": str(uuid4()), "text": marker},
                )
                assert held_from_provider.status_code == 200, held_from_provider.text
                assert held_from_provider.json()["evidence_status"] == "insufficient"
                assert held_from_provider.json()["citations"] == []
                assert external_calls == []

            transferable_marker = f"transferprobe{uuid4().hex}"
            transferable_source, transferable_revision = await _seed_source(
                factory, transferable_marker, provider_transfer=True
            )
            seeded_sources.append((transferable_source, transferable_revision))
            assert await ApprovedTextIndexer(factory, index).index_one() == transferable_revision
            transfer_calls: list[httpx.Request] = []

            def transfer_handler(request: httpx.Request) -> httpx.Response:
                transfer_calls.append(request)
                sent = request.content.decode()
                wire = json.loads(sent)
                evidence = json.loads(wire["messages"][-1]["content"])["evidence"]
                return httpx.Response(
                    200,
                    json={
                        "choices": [{"finish_reason": "stop", "message": {"content": json.dumps({
                            "fact": evidence[0]["excerpt"],
                            "interpretation": "The source describes only this synthetic count.",
                            "creative": "Make a new labelled concept from this test brief.",
                            "citations": [evidence[0]["id"]],
                        })}}],
                        "usage": {"prompt_tokens": 43, "completion_tokens": 17},
                    },
                )

            async with httpx.AsyncClient(transport=httpx.MockTransport(transfer_handler)) as client:
                app.state.model_provider = HttpModelProvider(
                    endpoint="https://approved.example/v1/chat/completions",
                    model="pilot-model", api_key="synthetic-key", policy_approved=True,
                    client=client,
                )
                transferred = owner.post(
                    f"/api/v1/chats/{chat_id}/messages", headers=owner_headers,
                    json={"request_id": str(uuid4()), "text": transferable_marker},
                )
                assert transferred.status_code == 200, transferred.text
                assert transferred.json()["evidence_status"] == "grounded"
                assert transferred.json()["citations"][0]["revision_id"] == str(
                    transferable_revision
                )
                assert len(transfer_calls) == 1
                sent = transfer_calls[0].content.decode()
                wire = json.loads(sent)
                evidence = json.loads(wire["messages"][-1]["content"])["evidence"]
                assert wire["model"] == "pilot-model"
                assert transfer_calls[0].headers["authorization"] == "Bearer synthetic-key"
                assert [item["revision_id"] for item in evidence] == [
                    str(transferable_revision)
                ]
                assert marker not in sent
                assert names[0] not in sent
                assert "synthetic-key" not in sent
            app.state.model_provider = default_provider
            transfer_revoke = admin.post(
                f"/api/v1/admin/revisions/{transferable_revision}/revoke",
                json={"reason": "Synthetic provider-transfer path completed"},
                headers=admin_headers,
            )
            assert transfer_revoke.status_code == 200, transfer_revoke.text
            assert (
                owner.get(f"/api/v1/chats/{chat_id}").json()["turns"][2]["citations"][0][
                    "available"
                ]
                is False
            )
            broken_id = str(uuid4())
            app.state.model_provider = BrokenProvider()
            broken_payload = {"request_id": broken_id, "text": marker}
            broken = owner.post(
                f"/api/v1/chats/{chat_id}/messages", headers=owner_headers, json=broken_payload
            )
            assert broken.status_code == 503, broken.text
            app.state.model_provider = default_provider
            recovered = owner.post(
                f"/api/v1/chats/{chat_id}/messages", headers=owner_headers, json=broken_payload
            )
            assert recovered.status_code == 200, recovered.text
            assert recovered.json()["evidence_status"] == "grounded"
            assert recovered.json()["citations"][0]["revision_id"] == str(revision_id)
            assert recovered.json()["citations"][0]["available"] is True
            assert len(owner.get(f"/api/v1/chats/{chat_id}").json()["turns"]) == 4
            revoked = admin.post(
                f"/api/v1/admin/revisions/{revision_id}/revoke",
                json={"reason": "Synthetic citation withdrawal check"},
                headers=admin_headers,
            )
            assert revoked.status_code == 200, revoked.text
            assert (
                owner.get(f"/api/v1/chats/{chat_id}").json()["turns"][3]["citations"][0][
                    "available"
                ]
                is False
            )
            assert owner.get(f"/api/v1/materials/{revision_id}").status_code == 404
            assert owner.get("/api/v1/materials", params={"q": marker}).json() == []
            assert (
                owner.delete(f"/api/v1/chats/{chat_id}", headers=owner_headers).status_code == 204
            )
            assert owner.get(f"/api/v1/chats/{chat_id}").status_code == 404

            expiring = owner.post("/api/v1/chats", headers=owner_headers).json()["id"]
            async with factory.begin() as session:
                row = await session.get(ChatConversation, UUID(expiring))
                assert row is not None
                row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            assert await SqlChatStore(factory).purge_expired() >= 1
            assert owner.get(f"/api/v1/chats/{expiring}").status_code == 404
    finally:
        if chat_id is not None:
            async with factory.begin() as session:
                await session.execute(
                    delete(ChatConversation).where(ChatConversation.id == UUID(chat_id))
                )
        for source_id, revision_id in reversed(seeded_sources):
            async with factory() as session:
                segments = (
                    await session.scalars(
                        select(SourceSegment).where(SourceSegment.revision_id == revision_id)
                    )
                ).all()
            await index.delete([segment.id for segment in segments])
            async with factory.begin() as session:
                await session.execute(
                    delete(SourceDecision).where(SourceDecision.revision_id == revision_id)
                )
                await session.execute(
                    delete(SourceSegment).where(SourceSegment.revision_id == revision_id)
                )
                await session.execute(
                    delete(SourceVectorIndex).where(SourceVectorIndex.revision_id == revision_id)
                )
                await session.execute(
                    delete(SourceProcessing).where(SourceProcessing.revision_id == revision_id)
                )
                await session.execute(
                    delete(SourceRevision).where(SourceRevision.id == revision_id)
                )
                await session.execute(delete(Source).where(Source.id == source_id))
        await engine.dispose()
