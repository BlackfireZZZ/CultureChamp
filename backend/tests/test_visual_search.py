"""Synthetic PDF visual search with exact page and current rights checks."""

import asyncio
import os
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pdf_fixture import self_authored_pdf
from PIL import Image, ImageDraw
from pypdf import PdfReader, PdfWriter
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.application.access import Role
from app.application.identity import IdentityService
from app.infrastructure.db.identity_store import SqlIdentityStore
from app.infrastructure.ingestion.processing import process_one
from app.infrastructure.ingestion.storage import PrivateOriginalStore
from app.infrastructure.ingestion.visual_storage import PrivateVisualStore
from app.infrastructure.passwords import Argon2PasswordCodec
from app.infrastructure.vector.visual_indexing import ApprovedVisualIndexer
from app.infrastructure.vector.visual_vectors import DIMENSIONS, QdrantVisualIndex
from app.main import create_app


class ConstantVisualEmbedder:
    async def query(self, text: str) -> list[float]:
        return [1.0] + [0.0] * (DIMENSIONS - 1)

    async def images(self, paths: list[str]) -> list[list[float]]:
        return [[1.0] + [0.0] * (DIMENSIONS - 1) for _ in paths]


def image_pdf() -> bytes:
    image = Image.new("RGB", (300, 300), "white")
    ImageDraw.Draw(image).ellipse((50, 50, 250, 250), fill="red")
    picture = BytesIO()
    image.save(picture, format="PDF")
    picture.seek(0)
    writer = PdfWriter()
    page = writer.add_page(
        PdfReader(BytesIO(self_authored_pdf("Self authored red circle"))).pages[0]
    )
    page.merge_page(PdfReader(picture).pages[0])
    result = BytesIO()
    writer.write(result)
    return result.getvalue()


def test_visual_pdf_search_approval_page_and_revocation(tmp_path: Path) -> None:
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
    index = QdrantVisualIndex(vector_url, ConstantVisualEmbedder())
    app.state.visual_index = index
    indexer = ApprovedVisualIndexer(factory, index, store, PrivateVisualStore(tmp_path / "private"))
    password = "synthetic-visual-password"
    admin_name, user_name = f"admin-{uuid4().hex[:12]}", f"user-{uuid4().hex[:12]}"

    async def seed() -> None:
        await identity_store.create_account(admin_name, await codec.hash(password), Role.ADMIN)
        await identity_store.create_account(user_name, await codec.hash(password), Role.USER)

    asyncio.run(seed())
    origin = "http://testserver"
    with TestClient(app, base_url=origin) as admin, TestClient(app, base_url=origin) as user:
        query = "/api/v1/materials/visual-search?q=red+circle"
        assert user.get(query).status_code == 401
        admin_login = admin.post(
            "/api/v1/auth/login",
            json={"username": admin_name, "password": password},
            headers={"origin": origin},
        )
        user_login = user.post(
            "/api/v1/auth/login",
            json={"username": user_name, "password": password},
            headers={"origin": origin},
        )
        assert admin_login.status_code == user_login.status_code == 200
        headers = {"origin": origin, "x-csrf-token": admin_login.json()["csrf_token"]}
        upload = admin.post(
            "/api/v1/admin/sources",
            headers=headers,
            data={
                "origin_url": "https://example.invalid/visual",
                "title": "Synthetic red circle",
                "rights_note": "Self-authored fixture",
            },
            files={"file": ("circle.pdf", image_pdf(), "application/pdf")},
        )
        assert upload.status_code == 201, upload.text
        revision_id = UUID(upload.json()["revision_id"])
        assert admin.get(query).status_code == 403
        assert user.get("/api/v1/materials/visual-search?q=x").status_code == 422
        assert user.get(query).json() == []
        assert asyncio.run(process_one(factory, store)) == revision_id
        approval = admin.post(
            f"/api/v1/admin/revisions/{revision_id}/approve",
            headers=headers,
            json={
                "reason": "Self-authored visual test fixture",
                "evidence_url": "https://example.invalid/rights",
                "user_text": True,
                "original_file": True,
                "provider_transfer": False,
                "sensitivity_cleared": True,
            },
        )
        assert approval.status_code == 200, approval.text
        assert asyncio.run(indexer.index_one()) == revision_id
        results = user.get(query)
        assert results.status_code == 200, results.text
        assert len(results.json()) == 1
        assert results.json()[0]["revision_id"] == str(revision_id)
        assert results.json()[0]["page"] == 1
        point_id = UUID(results.json()[0]["image_id"])
        asyncio.run(index.delete([point_id]))
        assert asyncio.run(indexer.audit_one()) == revision_id
        assert asyncio.run(indexer.index_one()) == revision_id
        assert user.get(f"/api/v1/materials/{revision_id}/original").status_code == 200
        revoked = admin.post(
            f"/api/v1/admin/revisions/{revision_id}/revoke",
            headers=headers,
            json={"reason": "End synthetic visual fixture"},
        )
        assert revoked.status_code == 200, revoked.text
        assert user.get(query).json() == []
        assert user.get(f"/api/v1/materials/{revision_id}/original").status_code == 404
        assert asyncio.run(indexer.remove_revoked_one()) == revision_id
    asyncio.run(engine.dispose())
