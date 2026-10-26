import asyncio
import os
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.application.generation import GeneratedAnswer
from app.infrastructure.db.chat_models import ChatConversation
from app.infrastructure.db.chat_store import SqlChatStore
from app.infrastructure.db.identity_models import Account


def test_late_stream_failure_cannot_erase_committed_chat_answer() -> None:
    url = os.getenv("CORPUS_TEST_DATABASE_URL")
    if url is None:
        pytest.skip("set CORPUS_TEST_DATABASE_URL for PostgreSQL integration")

    async def check():
        engine = create_async_engine(url, poolclass=NullPool)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        owner, request_id = uuid4(), uuid4()
        store = SqlChatStore(factory)
        try:
            async with factory.begin() as session:
                session.add(Account(id=owner, username=f"late-failure-{owner.hex}",
                                    password_hash="synthetic-only", role="user"))
            chat = await store.create(str(owner))
            claim = await store.claim(str(owner), chat.id, request_id, "Synthetic task", None)
            assert claim.attempt is not None
            answer = GeneratedAnswer("Synthetic completed answer", (), "insufficient")
            completed = await store.finish(str(owner), chat.id, request_id, claim.attempt, answer)
            await store.fail(str(owner), chat.id, request_id, claim.attempt)
            retry = await store.claim(str(owner), chat.id, request_id, "Synthetic task", None)
            assert retry.attempt is None
            assert retry.completed == completed
            next_request = uuid4()
            pending = await store.claim(str(owner), chat.id, next_request, "Next task", None)
            await store.fail(str(owner), chat.id, next_request, pending.attempt)
            detail = await store.detail(str(owner), chat.id)
            assert [turn.status for turn in detail.turns] == ["complete", "failed"]
        finally:
            async with factory.begin() as session:
                await session.execute(delete(ChatConversation).where(
                    ChatConversation.owner_id == owner
                ))
                await session.execute(delete(Account).where(Account.id == owner))
            await engine.dispose()

    asyncio.run(check())
