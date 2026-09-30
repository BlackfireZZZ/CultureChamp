import asyncio
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.application.access import Role
from app.application.identity import IdentityService
from app.infrastructure.db.identity_models import LoginSession
from app.infrastructure.db.identity_store import SqlIdentityStore
from app.infrastructure.passwords import Argon2PasswordCodec
from app.main import create_app

PASSWORD = "correct-horse-battery-2026"


def test_real_app_sessions_roles_csrf_expiry_and_logout() -> None:
    url = os.getenv("CORPUS_TEST_DATABASE_URL")
    if url is None:
        pytest.skip("set CORPUS_TEST_DATABASE_URL for PostgreSQL integration")
    engine = create_async_engine(url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    store = SqlIdentityStore(factory)
    codec = Argon2PasswordCodec()
    service = IdentityService(store, codec, codec.dummy_hash)
    admin_name = f"admin-{uuid4().hex[:12]}"
    user_name = f"user-{uuid4().hex[:12]}"

    async def seed() -> None:
        await store.create_account(admin_name, await codec.hash(PASSWORD), Role.ADMIN)
        await store.create_account(user_name, await codec.hash(PASSWORD), Role.USER)

    asyncio.run(seed())
    app = create_app()
    app.state.session_store = store
    app.state.identity_service = service
    origin = "http://testserver"
    with (
        TestClient(app, base_url=origin) as admin_client,
        TestClient(app, base_url=origin) as user_client,
    ):
        assert admin_client.get("/api/v1/auth/me").status_code == 401
        assert (
            admin_client.post(
                "/api/v1/auth/login",
                json={"username": admin_name, "password": PASSWORD},
                headers={"origin": "http://evil.test"},
            ).status_code
            == 403
        )
        wrong = admin_client.post(
            "/api/v1/auth/login",
            json={"username": admin_name, "password": "wrong-password"},
            headers={"origin": origin},
        )
        unknown = admin_client.post(
            "/api/v1/auth/login",
            json={"username": "unknown-account", "password": "wrong-password"},
            headers={"origin": origin},
        )
        assert wrong.status_code == unknown.status_code == 401
        admin_login = admin_client.post(
            "/api/v1/auth/login",
            json={"username": admin_name, "password": PASSWORD},
            headers={"origin": origin},
        )
        user_login = user_client.post(
            "/api/v1/auth/login",
            json={"username": user_name, "password": PASSWORD},
            headers={"origin": origin},
        )
        assert admin_login.status_code == user_login.status_code == 200
        assert admin_login.json()["user"]["role"] == "admin"
        assert user_login.json()["user"]["role"] == "user"
        assert "httponly" in admin_login.headers["set-cookie"].lower()
        assert admin_client.get("/api/v1/auth/me").json()["user"]["username"] == admin_name

        account_path = "/api/v1/admin/accounts"
        assert (
            user_client.post(account_path, json={}, headers={"origin": origin}).status_code == 403
        )
        assert (
            admin_client.post(
                account_path,
                json={"username": "new-user", "password": PASSWORD},
                headers={"origin": origin},
            ).status_code
            == 403
        )
        created = admin_client.post(
            account_path,
            json={"username": f"new-{uuid4().hex[:12]}", "password": PASSWORD},
            headers={"origin": origin, "x-csrf-token": admin_login.json()["csrf_token"]},
        )
        assert created.status_code == 201
        assert created.json()["role"] == "user"

        async def expire() -> None:
            async with factory.begin() as session:
                await session.execute(
                    update(LoginSession)
                    .where(LoginSession.account_id == user_login.json()["user"]["id"])
                    .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
                )

        asyncio.run(expire())
        assert user_client.get("/api/v1/auth/me").status_code == 401
        assert (
            admin_client.post(
                "/api/v1/auth/logout",
                headers={"origin": origin, "x-csrf-token": admin_login.json()["csrf_token"]},
            ).status_code
            == 204
        )
        assert admin_client.get("/api/v1/auth/me").status_code == 401
    asyncio.run(engine.dispose())
