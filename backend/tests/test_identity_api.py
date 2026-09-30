import asyncio
import hashlib
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.application.access import Role
from app.application.identity import IdentityService
from app.infrastructure.db.identity_models import Account, LoginSession
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

        async def inspect_secrets() -> None:
            async with factory() as session:
                account = await session.scalar(
                    select(Account).where(Account.username == admin_name)
                )
                assert account is not None and account.password_hash.startswith("$argon2id$")
                assert PASSWORD not in account.password_hash
                tokens = (await session.scalars(select(LoginSession.token_hash))).all()
                assert all(len(token) == 64 for token in tokens)
                assert admin_client.cookies.get("culturechamp-dev-session") not in tokens

        asyncio.run(inspect_secrets())
        prior_token = admin_client.cookies.get("culturechamp-dev-session")
        rotated = admin_client.post(
            "/api/v1/auth/login",
            json={"username": admin_name, "password": PASSWORD},
            headers={"origin": origin},
        )
        assert rotated.status_code == 200
        assert prior_token != admin_client.cookies.get("culturechamp-dev-session")

        async def old_session_revoked() -> None:
            assert prior_token is not None
            async with factory() as session:
                old = await session.get(
                    LoginSession, hashlib.sha256(prior_token.encode()).hexdigest()
                )
                assert old is not None and old.revoked_at is not None

        asyncio.run(old_session_revoked())
        admin_login = rotated

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


def test_login_throttle_has_generic_credentials_error_then_429() -> None:
    url = os.getenv("CORPUS_TEST_DATABASE_URL")
    if url is None:
        pytest.skip("set CORPUS_TEST_DATABASE_URL for PostgreSQL integration")
    engine = create_async_engine(url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    store = SqlIdentityStore(factory)
    codec = Argon2PasswordCodec()
    app = create_app()
    app.state.session_store = store
    app.state.identity_service = IdentityService(store, codec, codec.dummy_hash)
    origin = "http://testserver"
    name = f"missing-{uuid4().hex[:12]}"
    with TestClient(app, base_url=origin) as client:
        statuses = [
            client.post(
                "/api/v1/auth/login",
                json={"username": name, "password": "incorrect-password"},
                headers={"origin": origin},
            ).status_code
            for _ in range(6)
        ]
        assert statuses == [401, 401, 401, 401, 401, 429]
    asyncio.run(engine.dispose())
