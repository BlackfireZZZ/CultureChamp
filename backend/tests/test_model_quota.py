import asyncio
import os
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.infrastructure.db.chat_models import GenerationReservation
from app.infrastructure.db.identity_models import Account
from app.infrastructure.db.model_quota import SqlModelQuota
from app.infrastructure.model.gateway import ModelResult


def test_shared_quota_retries_failed_request_and_limits_daily_calls() -> None:
    url = os.getenv("CORPUS_TEST_DATABASE_URL")
    if url is None:
        pytest.skip("set CORPUS_TEST_DATABASE_URL for PostgreSQL integration")
    asyncio.run(_check_quota(url))


async def _check_quota(url: str) -> None:
    engine = create_async_engine(url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    account_id = uuid4()
    quota = SqlModelQuota(factory)
    subject = str(account_id)
    try:
        async with factory.begin() as session:
            session.add(
                Account(
                    id=account_id,
                    username=f"quota-{account_id.hex[:12]}",
                    password_hash="synthetic-test-only",
                    role="user",
                )
            )
        first = str(uuid4())
        assert await quota.reserve(subject, first)
        assert not await quota.reserve(subject, str(uuid4()))
        await quota.finish(subject, first, None)
        assert await quota.reserve(subject, first)
        await quota.finish(subject, first, ModelResult("ok", 5, 2))
        assert not await quota.reserve(subject, first)
        for _ in range(19):
            key = str(uuid4())
            assert await quota.reserve(subject, key)
            await quota.finish(subject, key, ModelResult("ok", 5, 2))
        assert not await quota.reserve(subject, str(uuid4()))
    finally:
        async with factory.begin() as session:
            await session.execute(
                delete(GenerationReservation).where(GenerationReservation.subject_id == account_id)
            )
            await session.execute(delete(Account).where(Account.id == account_id))
        await engine.dispose()
