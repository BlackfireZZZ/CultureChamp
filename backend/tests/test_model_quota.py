import asyncio
import os
from datetime import UTC, datetime, time, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.infrastructure.db.model_quota as quota_module
from app.infrastructure.db.chat_models import (
    ChatConversation,
    ChatTurn,
    GenerationAttempt,
    GenerationReservation,
)
from app.infrastructure.db.identity_models import Account
from app.infrastructure.db.model_quota import SqlModelQuota
from app.infrastructure.model.gateway import ModelResult


def test_shared_quota_retries_failed_request_and_limits_daily_calls() -> None:
    url = os.getenv("CORPUS_TEST_DATABASE_URL")
    if url is None:
        pytest.skip("set CORPUS_TEST_DATABASE_URL for PostgreSQL integration")
    asyncio.run(_check_quota(url))


def test_global_daily_quota_counts_failed_retry_across_users(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = os.getenv("CORPUS_TEST_DATABASE_URL")
    if url is None:
        pytest.skip("set CORPUS_TEST_DATABASE_URL for PostgreSQL integration")
    asyncio.run(_check_global_quota(url, monkeypatch))


def test_provider_success_with_failed_chat_can_retry_without_losing_usage() -> None:
    url = os.getenv("CORPUS_TEST_DATABASE_URL")
    if url is None:
        pytest.skip("set CORPUS_TEST_DATABASE_URL for PostgreSQL integration")

    async def check():
        engine = create_async_engine(url, poolclass=NullPool)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        account_id, chat_id, request_id = uuid4(), uuid4(), uuid4()
        quota = SqlModelQuota(factory)
        try:
            async with factory.begin() as session:
                session.add(Account(id=account_id, username=f"retry-{account_id.hex}",
                                    password_hash="synthetic-only", role="user"))
                await session.flush()
                session.add(ChatConversation(
                    id=chat_id, owner_id=account_id, title="Synthetic retry",
                    expires_at=datetime.now(UTC) + timedelta(days=1),
                ))
                await session.flush()
                session.add(ChatTurn(id=request_id, conversation_id=chat_id, ordinal=0,
                                     user_text="Synthetic task", status="failed", attempt=1))
            assert await quota.reserve(str(account_id), str(request_id))
            await quota.finish(str(account_id), str(request_id), ModelResult("ok", 5, 2))
            assert not await quota.reserve(str(account_id), str(request_id))
            async with factory.begin() as session:
                turn = await session.get(ChatTurn, request_id)
                turn.status = "pending"
                turn.lease_until = datetime.now(UTC) + timedelta(seconds=120)
            assert not await quota.reserve(str(account_id), str(request_id))
            async with factory.begin() as session:
                turn = await session.get(ChatTurn, request_id)
                turn.attempt = 2
                turn.lease_until = datetime.now(UTC) - timedelta(seconds=1)
            assert not await quota.reserve(str(account_id), str(request_id))
            async with factory.begin() as session:
                turn = await session.get(ChatTurn, request_id)
                turn.lease_until = datetime.now(UTC) + timedelta(seconds=120)
            assert await quota.reserve(str(account_id), str(request_id))
            assert not await quota.reserve(str(account_id), str(request_id))
            await quota.finish(str(account_id), str(request_id), ModelResult("ok", 7, 3))
            async with factory.begin() as session:
                turn = await session.get(ChatTurn, request_id)
                turn.status = "complete"
                turn.lease_until = None
            assert not await quota.reserve(str(account_id), str(request_id))
            async with factory() as session:
                attempts = (await session.scalars(
                    select(GenerationAttempt).where(
                        GenerationAttempt.reservation_id == request_id
                    ).order_by(GenerationAttempt.id)
                )).all()
                assert [(row.input_tokens, row.output_tokens) for row in attempts] == [
                    (5, 2), (7, 3)
                ]
        finally:
            async with factory.begin() as session:
                await session.execute(delete(ChatConversation).where(
                    ChatConversation.id == chat_id
                ))
                await session.execute(delete(GenerationReservation).where(
                    GenerationReservation.subject_id == account_id
                ))
                await session.execute(delete(Account).where(Account.id == account_id))
            await engine.dispose()

    asyncio.run(check())


async def _check_global_quota(url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_async_engine(url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    ids = (uuid4(), uuid4())
    quota = SqlModelQuota(factory)
    try:
        day_start = datetime.combine(datetime.now(UTC).date(), time.min, tzinfo=UTC)
        async with factory() as session:
            existing = await session.scalar(
                select(func.count()).select_from(GenerationAttempt)
                .where(GenerationAttempt.created_at >= day_start)
            )
        monkeypatch.setattr(quota_module, "GLOBAL_DAILY_LIMIT", (existing or 0) + 2)
        async with factory.begin() as session:
            for account_id in ids:
                session.add(Account(
                    id=account_id,
                    username=f"quota-global-{account_id.hex[:12]}",
                    password_hash="synthetic-test-only",
                    role="user",
                ))
        key = str(uuid4())
        assert await quota.reserve(str(ids[0]), key)
        await quota.finish(str(ids[0]), key, None)
        assert await quota.reserve(str(ids[0]), key)
        await quota.finish(str(ids[0]), key, None)
        assert not await quota.reserve(str(ids[1]), str(uuid4()))
    finally:
        async with factory.begin() as session:
            await session.execute(
                delete(GenerationReservation).where(GenerationReservation.subject_id.in_(ids))
            )
            await session.execute(delete(Account).where(Account.id.in_(ids)))
        await engine.dispose()


async def _check_quota(url: str) -> None:
    engine = create_async_engine(url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    account_id = uuid4()
    failing_account_id = uuid4()
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
            session.add(
                Account(
                    id=failing_account_id,
                    username=f"quota-failed-{failing_account_id.hex[:12]}",
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
        async with factory() as session:
            first_attempts = (
                await session.scalars(
                    select(GenerationAttempt)
                    .where(GenerationAttempt.reservation_id == UUID(first))
                    .order_by(GenerationAttempt.id)
                )
            ).all()
            assert [(attempt.accepted, attempt.input_tokens, attempt.output_tokens)
                    for attempt in first_attempts] == [(False, None, None), (True, 5, 2)]
        rejected = str(uuid4())
        assert await quota.reserve(subject, rejected)
        await quota.finish(subject, rejected, ModelResult("too long", 7, 4), accepted=False)
        assert await quota.reserve(subject, rejected)
        await quota.finish(subject, rejected, None)
        async with factory() as session:
            rejected_attempts = (
                await session.scalars(
                    select(GenerationAttempt)
                    .where(GenerationAttempt.reservation_id == UUID(rejected))
                    .order_by(GenerationAttempt.id)
                )
            ).all()
            assert [(attempt.accepted, attempt.input_tokens, attempt.output_tokens)
                    for attempt in rejected_attempts] == [(False, 7, 4), (False, None, None)]
        assert not await quota.reserve(subject, first)
        for _ in range(16):
            key = str(uuid4())
            assert await quota.reserve(subject, key)
            await quota.finish(subject, key, ModelResult("ok", 5, 2))
        assert not await quota.reserve(subject, str(uuid4()))
        failed_subject = str(failing_account_id)
        failed_key = str(uuid4())
        for _ in range(20):
            assert await quota.reserve(failed_subject, failed_key)
            await quota.finish(failed_subject, failed_key, None)
        assert not await quota.reserve(failed_subject, failed_key)
        assert not await quota.reserve(failed_subject, str(uuid4()))
    finally:
        async with factory.begin() as session:
            await session.execute(
                delete(GenerationReservation).where(
                    GenerationReservation.subject_id.in_((account_id, failing_account_id))
                )
            )
            await session.execute(
                delete(Account).where(Account.id.in_((account_id, failing_account_id)))
            )
        await engine.dispose()
