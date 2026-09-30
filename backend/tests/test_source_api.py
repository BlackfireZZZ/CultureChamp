import asyncio
import os
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.application.access import Role
from app.application.identity import IdentityService
from app.infrastructure.db.identity_store import SqlIdentityStore
from app.infrastructure.ingestion.processing import process_one
from app.infrastructure.ingestion.storage import PrivatePdfStore
from app.infrastructure.passwords import Argon2PasswordCodec
from app.main import create_app

PASSWORD = "fixture-account-password-2026"


def _self_authored_pdf(text: str = "Self authored permitted fixture") -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 30 200 Td ({text}) Tj ET".encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    result = BytesIO()
    writer.write(result)
    return result.getvalue()


def test_admin_upload_review_approval_user_visibility_and_revocation(tmp_path: Path) -> None:
    url = os.getenv("CORPUS_TEST_DATABASE_URL")
    if url is None:
        pytest.skip("set CORPUS_TEST_DATABASE_URL for PostgreSQL integration")
    engine = create_async_engine(url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    identity_store = SqlIdentityStore(factory)
    codec = Argon2PasswordCodec()
    app = create_app()
    app.state.session_store = identity_store
    app.state.identity_service = IdentityService(identity_store, codec, codec.dummy_hash)
    app.state.source_session_factory = factory
    private_store = PrivatePdfStore(tmp_path / "private", public_root=tmp_path / "public")
    app.state.source_store = private_store
    admin_name, user_name = f"admin-{uuid4().hex[:12]}", f"user-{uuid4().hex[:12]}"

    async def seed() -> None:
        await identity_store.create_account(admin_name, await codec.hash(PASSWORD), Role.ADMIN)
        await identity_store.create_account(user_name, await codec.hash(PASSWORD), Role.USER)

    asyncio.run(seed())
    origin = "http://testserver"
    with (
        TestClient(app, base_url=origin) as admin,
        TestClient(app, base_url=origin) as user,
    ):

        def login(client: TestClient, username: str) -> dict[str, str]:
            response = client.post(
                "/api/v1/auth/login",
                json={"username": username, "password": PASSWORD},
                headers={"origin": origin},
            )
            assert response.status_code == 200
            return {"origin": origin, "x-csrf-token": response.json()["csrf_token"]}

        admin_headers, user_headers = login(admin, admin_name), login(user, user_name)
        payload = _self_authored_pdf()
        form = {"origin_url": "https://example.invalid/owned-fixture", "title": "Owned fixture"}

        def send_file(client: TestClient, headers: dict[str, str], data: bytes, **fields: str):
            return client.post(
                "/api/v1/admin/sources",
                headers=headers,
                data={**form, **fields},
                files={"file": ("fixture.pdf", data, "application/pdf")},
            )

        assert send_file(user, user_headers, payload).status_code == 403
        assert send_file(admin, admin_headers, b"%PDF-1.4\nnot a file").status_code == 422
        uploaded = send_file(admin, admin_headers, payload, tags="region:Primorye")
        assert uploaded.status_code == 201, uploaded.text
        source_id = uploaded.json()["source_id"]
        revision_id = uploaded.json()["revision_id"]
        assert uploaded.json()["status"] == "candidate"
        assert user.get("/api/v1/materials").json() == []
        assert user.get(f"/api/v1/materials/{revision_id}").status_code == 404
        assert user.get(f"/api/v1/materials/{revision_id}/original").status_code == 404
        assert user.get(f"/api/v1/materials/{uuid4()}").status_code == 404
        assert user.get(f"/api/v1/admin/revisions/{revision_id}").status_code == 403
        assert user.get("/api/v1/admin/sources").status_code == 403
        assert any(
            item["revision_id"] == revision_id for item in admin.get("/api/v1/admin/sources").json()
        )
        assert admin.get(f"/api/v1/admin/revisions/{revision_id}").json()["status"] == "candidate"
        assert any(
            item["revision_id"] == revision_id
            for item in admin.get("/api/v1/admin/sources?status=candidate&decision=none").json()
        )

        duplicate = send_file(
            admin, admin_headers, payload, source_id=source_id, tags="region:Other"
        )
        assert duplicate.status_code == 201
        assert duplicate.json()["revision_id"] == revision_id
        assert asyncio.run(process_one(factory, private_store)) == UUID(revision_id)
        assert asyncio.run(process_one(factory, private_store)) is None
        review = admin.get(f"/api/v1/admin/revisions/{revision_id}")
        assert review.status_code == 200
        assert review.json()["status"] == "review_pending"
        assert review.json()["tags"] == [{"kind": "region", "value": "Primorye"}]
        assert review.json()["segments"][0]["locator"] == {"kind": "page", "page": 1}
        assert "Self authored" in review.json()["segments"][0]["text"]
        assert user.get("/api/v1/materials").json() == []
        approval = {
            "reason": "Reviewer confirmed this fixture was created for the integration test",
            "evidence_url": "https://example.invalid/owned-fixture/rights",
            "user_text": True,
            "original_file": False,
            "provider_transfer": False,
            "sensitivity_cleared": True,
        }
        assert (
            admin.post(f"/api/v1/admin/revisions/{revision_id}/approve", json=approval).status_code
            == 403
        )
        approved = admin.post(
            f"/api/v1/admin/revisions/{revision_id}/approve", json=approval, headers=admin_headers
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["decision"] == "approve"
        assert [item["revision_id"] for item in user.get("/api/v1/materials").json()] == [
            revision_id
        ]
        assert (
            user.get(f"/api/v1/materials/{revision_id}").json()["segments"][0]["locator"]["page"]
            == 1
        )
        assert user.get(f"/api/v1/materials/{revision_id}").json()["original_available"] is False
        assert user.get(f"/api/v1/materials/{revision_id}/original").status_code == 404
        revoked = admin.post(
            f"/api/v1/admin/revisions/{revision_id}/revoke",
            json={"reason": "Fixture publication test completed"},
            headers=admin_headers,
        )
        assert revoked.status_code == 200, revoked.text
        assert user.get("/api/v1/materials").json() == []
        assert user.get(f"/api/v1/materials/{revision_id}").status_code == 404
        assert admin.get(f"/api/v1/admin/revisions/{revision_id}").json()["decision"] == "revoke"
        assert any(
            item["revision_id"] == revision_id
            for item in admin.get("/api/v1/admin/sources?decision=revoke&limit=1").json()
        )

        downloadable = _self_authored_pdf("Self authored original allowed")
        second = send_file(admin, admin_headers, downloadable)
        assert second.status_code == 201
        second_id = second.json()["revision_id"]
        assert asyncio.run(process_one(factory, private_store)) == UUID(second_id)
        allowed = {**approval, "original_file": True}
        assert (
            admin.post(
                f"/api/v1/admin/revisions/{second_id}/approve",
                json=allowed,
                headers=admin_headers,
            ).status_code
            == 200
        )
        assert user.get(f"/api/v1/materials/{second_id}").json()["original_available"] is True
        original = user.get(f"/api/v1/materials/{second_id}/original")
        assert original.status_code == 200
        assert original.content == downloadable
        assert original.headers["content-type"] == "application/pdf"
        assert original.headers["x-content-type-options"] == "nosniff"
        assert original.headers["cache-control"] == "no-store"
        assert "source-" in original.headers["content-disposition"]
        assert (
            admin.post(
                f"/api/v1/admin/revisions/{second_id}/revoke",
                json={"reason": "Original access check completed"},
                headers=admin_headers,
            ).status_code
            == 200
        )
        assert user.get(f"/api/v1/materials/{second_id}/original").status_code == 404

        broken = send_file(admin, admin_headers, b"%PDF-1.4\n%%EOF")
        assert broken.status_code == 201
        broken_id = broken.json()["revision_id"]
        assert asyncio.run(process_one(factory, private_store)) == UUID(broken_id)
        failed = admin.get(f"/api/v1/admin/revisions/{broken_id}").json()
        assert failed["status"] == "failed"
        assert failed["error_code"] == "pdf_extraction_failed"
        assert failed["segments"] == []
        assert failed["tags"] == []
        assert user.get(f"/api/v1/materials/{broken_id}").status_code == 404
        assert (
            admin.post(
                f"/api/v1/admin/revisions/{broken_id}/retry", headers=admin_headers
            ).status_code
            == 200
        )
        assert asyncio.run(process_one(factory, private_store)) == UUID(broken_id)
        assert admin.get(f"/api/v1/admin/revisions/{broken_id}").json()["status"] == "failed"
    asyncio.run(engine.dispose())
