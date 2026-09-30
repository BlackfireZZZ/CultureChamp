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
from xlsx_fixture import self_authored_formula_xlsx, self_authored_xlsx

from app.api.routes.sources import _detail_view
from app.application.access import Role
from app.application.identity import IdentityService
from app.application.source_management import MaterialData, SegmentData
from app.domain.sources import Locator
from app.infrastructure.db.identity_store import SqlIdentityStore
from app.infrastructure.db.vector_search import SqlGovernedVectorSearch
from app.infrastructure.ingestion.processing import process_one
from app.infrastructure.ingestion.storage import PrivateOriginalStore
from app.infrastructure.passwords import Argon2PasswordCodec
from app.infrastructure.vector.indexing import ApprovedTextIndexer
from app.infrastructure.vector.text_vectors import DIMENSIONS, QdrantTextIndex
from app.main import create_app

PASSWORD = "fixture-account-password-2026"


class ConstantEmbedder:
    async def query(self, text: str) -> list[float]:
        return [1.0] + [0.0] * (DIMENSIONS - 1)

    async def passages(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] + [0.0] * (DIMENSIONS - 1) for _ in texts]


def test_table_locator_is_not_rewritten_as_pdf_page() -> None:
    revision_id, segment_id = uuid4(), uuid4()
    detail = _detail_view(
        MaterialData(
            revision_id=revision_id,
            title="Self-authored synthetic table",
            creator=None,
            origin_url="https://example.invalid/table",
            rights_usage_note="Synthetic contract fixture",
            media_type="text/csv",
            segments=(
                SegmentData(
                    segment_id,
                    Locator(
                        sheet="Synthetic", row_start=3, row_end=3, column_start=2, column_end=2
                    ),
                    "Row 3, column 2: seven",
                ),
            ),
        )
    )
    locator = detail.segments[0].locator
    assert locator.kind == "table"
    assert locator.page is None
    assert (locator.sheet, locator.row_start, locator.column_start) == ("Synthetic", 3, 2)


def test_csv_upload_to_vector_and_original_access(tmp_path: Path) -> None:
    url = os.getenv("CORPUS_TEST_DATABASE_URL")
    vector_url = os.getenv("CORPUS_TEST_VECTOR_URL")
    if url is None or vector_url is None:
        pytest.skip("set CORPUS_TEST_DATABASE_URL and CORPUS_TEST_VECTOR_URL")
    engine = create_async_engine(url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    identity_store = SqlIdentityStore(factory)
    codec = Argon2PasswordCodec()
    app = create_app()
    app.state.session_store = identity_store
    app.state.identity_service = IdentityService(identity_store, codec, codec.dummy_hash)
    app.state.source_session_factory = factory
    store = PrivateOriginalStore(tmp_path / "private")
    app.state.source_store = store
    admin_name, user_name = f"admin-{uuid4().hex[:12]}", f"user-{uuid4().hex[:12]}"

    async def seed() -> None:
        await identity_store.create_account(admin_name, await codec.hash(PASSWORD), Role.ADMIN)
        await identity_store.create_account(user_name, await codec.hash(PASSWORD), Role.USER)

    asyncio.run(seed())
    payload = "Название,Регион,Число\r\nПробный объект,,7\r\n".encode()
    origin = "http://testserver"
    index = QdrantTextIndex(vector_url, ConstantEmbedder())
    with TestClient(app, base_url=origin) as admin, TestClient(app, base_url=origin) as user:
        admin_login = admin.post(
            "/api/v1/auth/login",
            json={"username": admin_name, "password": PASSWORD},
            headers={"origin": origin},
        )
        user_login = user.post(
            "/api/v1/auth/login",
            json={"username": user_name, "password": PASSWORD},
            headers={"origin": origin},
        )
        headers = {"origin": origin, "x-csrf-token": admin_login.json()["csrf_token"]}
        assert user_login.status_code == 200
        unsafe = admin.post(
            "/api/v1/admin/sources",
            headers=headers,
            data={"origin_url": "javascript:alert(1)", "title": "Unsafe origin"},
            files={"file": ("unsafe.csv", payload, "text/csv")},
        )
        assert unsafe.status_code == 422
        uploaded = admin.post(
            "/api/v1/admin/sources",
            headers=headers,
            data={"origin_url": "https://example.invalid/synthetic-csv", "title": "Synthetic CSV"},
            files={"file": ("fixture.csv", payload, "text/csv")},
        )
        assert uploaded.status_code == 201, uploaded.text
        revision_id = UUID(uploaded.json()["revision_id"])
        assert asyncio.run(process_one(factory, store)) == revision_id
        review = admin.get(f"/api/v1/admin/revisions/{revision_id}").json()
        assert review["media_type"] == "text/csv"
        assert review["status"] == "review_pending"
        assert len(review["segments"]) == 1
        segment = review["segments"][0]
        assert segment["text"] == "Название: Пробный объект; Число: 7"
        assert segment["locator"]["page"] is None
        assert (segment["locator"]["row_start"], segment["locator"]["column_start"]) == (2, 3)
        assert user.get(f"/api/v1/materials/{revision_id}").status_code == 404
        candidate_original = admin.get(f"/api/v1/admin/revisions/{revision_id}/original")
        assert candidate_original.status_code == 200
        assert candidate_original.content == payload
        assert candidate_original.headers["cache-control"] == "no-store"
        assert user.get(f"/api/v1/admin/revisions/{revision_id}/original").status_code == 403
        assert admin.get(f"/api/v1/admin/revisions/{uuid4()}/original").status_code == 404
        assert user.get(f"/api/v1/materials/{revision_id}/original").status_code == 404
        approved = admin.post(
            f"/api/v1/admin/revisions/{revision_id}/approve",
            json={
                "reason": "Self-authored synthetic table for technical verification",
                "evidence_url": "https://example.invalid/synthetic-csv/rights",
                "user_text": True, "original_file": True, "provider_transfer": False,
                "sensitivity_cleared": True,
            },
            headers=headers,
        )
        assert approved.status_code == 200, approved.text
        assert asyncio.run(ApprovedTextIndexer(factory, index).index_one()) == revision_id
        found = asyncio.run(SqlGovernedVectorSearch(factory, index).search(
            "Пробный объект число", limit=5, region=None, people=None, for_provider=False
        ))
        assert any(
            item.revision_id == revision_id and item.locator.column_start == 3 for item in found
        )
        detail = user.get(f"/api/v1/materials/{revision_id}")
        assert detail.json()["segments"][0]["segment_id"] == segment["segment_id"]
        original = user.get(f"/api/v1/materials/{revision_id}/original")
        assert original.content == payload
        assert original.headers["content-type"].startswith("text/csv")
        assert original.headers["content-disposition"].startswith("attachment;")
        assert admin.post(
            f"/api/v1/admin/revisions/{revision_id}/revoke",
            json={"reason": "Synthetic table check complete"}, headers=headers,
        ).status_code == 200
        assert user.get(f"/api/v1/materials/{revision_id}").status_code == 404
        assert user.get(f"/api/v1/materials/{revision_id}/original").status_code == 404
        assert admin.get(f"/api/v1/admin/revisions/{revision_id}/original").content == payload
        assert asyncio.run(SqlGovernedVectorSearch(factory, index).search(
            "Пробный объект число", limit=5, region=None, people=None, for_provider=False
        )) == ()
        assert asyncio.run(ApprovedTextIndexer(factory, index).remove_revoked_one()) == revision_id
    asyncio.run(engine.dispose())


def test_xlsx_sheet_locators_survive_approval_and_original_access(tmp_path: Path) -> None:
    url = os.getenv("CORPUS_TEST_DATABASE_URL")
    vector_url = os.getenv("CORPUS_TEST_VECTOR_URL")
    if url is None or vector_url is None:
        pytest.skip("set PostgreSQL and vector integration URLs")
    engine = create_async_engine(url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    identity_store = SqlIdentityStore(factory)
    codec = Argon2PasswordCodec()
    app = create_app()
    app.state.session_store = identity_store
    app.state.identity_service = IdentityService(identity_store, codec, codec.dummy_hash)
    app.state.source_session_factory = factory
    store = PrivateOriginalStore(tmp_path / "private")
    app.state.source_store = store
    admin_name, user_name = f"admin-{uuid4().hex[:12]}", f"user-{uuid4().hex[:12]}"

    async def seed() -> None:
        await identity_store.create_account(admin_name, await codec.hash(PASSWORD), Role.ADMIN)
        await identity_store.create_account(user_name, await codec.hash(PASSWORD), Role.USER)

    asyncio.run(seed())
    origin = "http://testserver"
    payload = self_authored_xlsx()
    mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    index = QdrantTextIndex(vector_url, ConstantEmbedder())
    with TestClient(app, base_url=origin) as admin, TestClient(app, base_url=origin) as user:
        admin_login = admin.post(
            "/api/v1/auth/login", json={"username": admin_name, "password": PASSWORD},
            headers={"origin": origin},
        )
        user_login = user.post(
            "/api/v1/auth/login", json={"username": user_name, "password": PASSWORD},
            headers={"origin": origin},
        )
        assert user_login.status_code == 200
        headers = {"origin": origin, "x-csrf-token": admin_login.json()["csrf_token"]}
        uploaded = admin.post(
            "/api/v1/admin/sources", headers=headers,
            data={"origin_url": "https://example.invalid/synthetic-xlsx",
                  "title": "Self-authored XLSX"},
            files={"file": ("table.xlsx", payload, mime)},
        )
        assert uploaded.status_code == 201, uploaded.text
        revision_id = UUID(uploaded.json()["revision_id"])
        assert asyncio.run(process_one(factory, store)) == revision_id
        review = admin.get(f"/api/v1/admin/revisions/{revision_id}").json()
        assert review["status"] == "review_pending"
        assert [(part["locator"]["sheet"], part["locator"]["row_start"],
                 part["locator"]["column_start"]) for part in review["segments"]] == [
            ("North", 2, 3), ("North", 3, 2), ("South", 2, 2),
        ]
        assert user.get(f"/api/v1/materials/{revision_id}").status_code == 404
        approved = admin.post(
            f"/api/v1/admin/revisions/{revision_id}/approve", headers=headers,
            json={"reason": "Self-authored workbook for technical verification",
                  "evidence_url": "https://example.invalid/synthetic-xlsx/rights",
                  "user_text": True, "original_file": True, "provider_transfer": False,
                  "sensitivity_cleared": True},
        )
        assert approved.status_code == 200, approved.text
        assert asyncio.run(ApprovedTextIndexer(factory, index).index_one()) == revision_id
        found = asyncio.run(SqlGovernedVectorSearch(factory, index).search(
            "Example A Count", limit=5, region=None, people=None, for_provider=False
        ))
        assert any(item.revision_id == revision_id and item.locator.sheet == "North"
                   and item.locator.row_start == 3 and item.locator.column_start == 2
                   for item in found)
        assert [part["segment_id"] for part in user.get(
            f"/api/v1/materials/{revision_id}"
        ).json()["segments"]] == [part["segment_id"] for part in review["segments"]]
        original = user.get(f"/api/v1/materials/{revision_id}/original")
        assert original.content == payload
        assert original.headers["content-type"].startswith(mime)
        assert original.headers["content-disposition"].endswith('.xlsx"')
        assert admin.post(
            f"/api/v1/admin/revisions/{revision_id}/revoke", headers=headers,
            json={"reason": "Synthetic workbook check complete"},
        ).status_code == 200
        assert user.get(f"/api/v1/materials/{revision_id}").status_code == 404
        assert user.get(f"/api/v1/materials/{revision_id}/original").status_code == 404
        rejected = admin.post(
            "/api/v1/admin/sources", headers=headers,
            data={"origin_url": "https://example.invalid/synthetic-formula",
                  "title": "Self-authored formula workbook"},
            files={"file": ("formula.xlsx", self_authored_formula_xlsx(), mime)},
        )
        assert rejected.status_code == 201
        rejected_id = UUID(rejected.json()["revision_id"])
        assert asyncio.run(process_one(factory, store)) == rejected_id
        failed = admin.get(f"/api/v1/admin/revisions/{rejected_id}").json()
        assert failed["status"] == "failed"
        assert failed["segments"] == []
        assert user.get(f"/api/v1/materials/{rejected_id}").status_code == 404
    asyncio.run(engine.dispose())


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
    private_store = PrivateOriginalStore(tmp_path / "private", public_root=tmp_path / "public")
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
        description = "Self-authored source for a technical catalogue check"
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
        uploaded = send_file(
            admin, admin_headers, payload, tags="region:Primorye",
            description=description,
        )
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
            admin, admin_headers, payload, source_id=source_id, tags="region:Other",
            description="A retry must not replace captured metadata",
        )
        assert duplicate.status_code == 201
        assert duplicate.json()["revision_id"] == revision_id
        assert asyncio.run(process_one(factory, private_store)) == UUID(revision_id)
        assert asyncio.run(process_one(factory, private_store)) is None
        review = admin.get(f"/api/v1/admin/revisions/{revision_id}")
        assert review.status_code == 200
        assert review.json()["status"] == "review_pending"
        assert review.json()["description"] == description
        assert review.json()["tags"] == [{"kind": "region", "value": "Primorye"}]
        assert review.json()["segments"][0]["locator"]["kind"] == "page"
        assert review.json()["segments"][0]["locator"]["page"] == 1
        assert "Self authored" in review.json()["segments"][0]["text"]
        filtered_inventory = admin.get(
            "/api/v1/admin/sources?q=owned-fixture&media_type=application/pdf"
            "&tag_kind=region&tag_value=Primorye"
        )
        assert revision_id in [item["revision_id"] for item in filtered_inventory.json()]
        for query in ("media_type=text/csv", "tag_kind=region&tag_value=Other", "q=%25"):
            assert revision_id not in [
                item["revision_id"] for item in admin.get(f"/api/v1/admin/sources?{query}").json()
            ]
        revised_description = f"{description}; reviewed after extraction"
        metadata_change = {
            "expected_version": 0,
            "reason": "Corrected the catalogue after comparing the original and extracted text",
            "description": revised_description,
            "tags": [
                {"kind": "region", "value": "Primorye"},
                {"kind": "topic", "value": "Fixture"},
            ],
        }
        assert admin.patch(
            f"/api/v1/admin/revisions/{revision_id}/metadata",
            json={**metadata_change, "tags": [metadata_change["tags"][0]] * 2},
            headers=admin_headers,
        ).status_code == 422
        assert admin.patch(
            f"/api/v1/admin/revisions/{revision_id}/metadata",
            json=metadata_change,
        ).status_code == 403
        assert user.patch(
            f"/api/v1/admin/revisions/{revision_id}/metadata",
            json=metadata_change, headers=user_headers,
        ).status_code == 403
        changed = admin.patch(
            f"/api/v1/admin/revisions/{revision_id}/metadata",
            json=metadata_change, headers=admin_headers,
        )
        assert changed.status_code == 200, changed.text
        assert changed.json()["metadata_version"] == 1
        assert changed.json()["description"] == revised_description
        assert changed.json()["tags"] == metadata_change["tags"]
        assert changed.json()["sha256"] == review.json()["sha256"]
        assert changed.json()["segments"] == review.json()["segments"]
        history = admin.get(f"/api/v1/admin/revisions/{revision_id}/metadata-history")
        assert history.status_code == 200
        assert [event["version"] for event in history.json()] == [0, 1]
        assert [event["description"] for event in history.json()] == [
            description, revised_description,
        ]
        assert history.json()[0]["tags"] == [{"kind": "region", "value": "Primorye"}]
        assert history.json()[1]["tags"] == metadata_change["tags"]
        assert send_file(
            admin, admin_headers, payload, source_id=source_id,
            description="Duplicate retry cannot replace reviewed metadata",
            tags="region:Other",
        ).json()["revision_id"] == revision_id
        assert admin.get(
            f"/api/v1/admin/revisions/{revision_id}"
        ).json()["description"] == revised_description
        assert user.get(
            f"/api/v1/admin/revisions/{revision_id}/metadata-history"
        ).status_code == 403
        assert admin.patch(
            f"/api/v1/admin/revisions/{revision_id}/metadata",
            json=metadata_change, headers=admin_headers,
        ).status_code == 409
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
            user.post(
                f"/api/v1/admin/revisions/{revision_id}/approve",
                json=approval,
                headers=user_headers,
            ).status_code
            == 403
        )
        assert (
            admin.post(
                f"/api/v1/admin/revisions/{revision_id}/approve",
                json={**approval, "evidence_url": "file:///untrusted/rights"},
                headers=admin_headers,
            ).status_code
            == 422
        )
        assert admin.get(f"/api/v1/admin/revisions/{revision_id}").json()["decision"] is None
        assert (
            admin.post(f"/api/v1/admin/revisions/{revision_id}/approve", json=approval).status_code
            == 403
        )
        approved = admin.post(
            f"/api/v1/admin/revisions/{revision_id}/approve", json=approval, headers=admin_headers
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["decision"] == "approve"
        assert admin.patch(
            f"/api/v1/admin/revisions/{revision_id}/metadata",
            json={**metadata_change, "expected_version": 1}, headers=admin_headers,
        ).status_code == 409
        visible_list = user.get("/api/v1/materials")
        assert visible_list.headers["cache-control"] == "no-store"
        assert [item["revision_id"] for item in visible_list.json()] == [revision_id]
        assert visible_list.json()[0]["region"] == "Primorye"
        assert visible_list.json()[0]["description"] == revised_description
        assert visible_list.json()[0]["tags"] == metadata_change["tags"]
        assert [item["revision_id"] for item in user.get(
            "/api/v1/materials?region=Primorye&q=Owned"
        ).json()] == [revision_id]
        assert [item["revision_id"] for item in user.get(
            "/api/v1/materials?q=technical%20catalogue"
        ).json()] == [revision_id]
        assert user.get("/api/v1/materials?region=Other").json() == []
        assert user.get("/api/v1/materials?q=%25").json() == []
        assert (
            user.get(f"/api/v1/materials/{revision_id}").json()["segments"][0]["locator"]["page"]
            == 1
        )
        text_detail = user.get(f"/api/v1/materials/{revision_id}")
        assert text_detail.headers["cache-control"] == "no-store"
        assert text_detail.json()["original_available"] is False
        assert user.get(f"/api/v1/materials/{revision_id}/original").status_code == 404
        revoked = admin.post(
            f"/api/v1/admin/revisions/{revision_id}/revoke",
            json={"reason": "Fixture publication test completed"},
            headers=admin_headers,
        )
        assert revoked.status_code == 200, revoked.text
        assert (
            user.post(
                f"/api/v1/admin/revisions/{revision_id}/revoke",
                json={"reason": "Unauthorized user request"},
                headers=user_headers,
            ).status_code
            == 403
        )
        assert user.get("/api/v1/materials").json() == []
        assert user.get("/api/v1/materials?region=Primorye").json() == []
        assert user.get(f"/api/v1/materials/{revision_id}").status_code == 404
        assert admin.get(f"/api/v1/admin/revisions/{revision_id}").json()["decision"] == "revoke"
        assert [event["version"] for event in admin.get(
            f"/api/v1/admin/revisions/{revision_id}/metadata-history"
        ).json()] == [0, 1]
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
        assert failed["error_code"] == "source_extraction_failed"
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
