"""PostgreSQL chat ownership, idempotent turns, citations and retention."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.chat import (
    ChatCitationData,
    ChatConflict,
    ChatData,
    ChatNotFound,
    ChatTurnData,
    TurnClaim,
)
from app.application.chat_titles import first_turn_title
from app.application.generation import GeneratedAnswer
from app.domain.sources import Locator
from app.infrastructure.db.chat_models import ChatCitation, ChatConversation, ChatTurn
from app.infrastructure.db.source_repository import SourceRepository

RETENTION = timedelta(days=30)
TURN_LEASE = timedelta(seconds=120)


class SqlChatStore:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self.factory = factory

    async def _owned(
        self, session: AsyncSession, owner: str, chat_id: UUID, *, lock: bool = False
    ) -> ChatConversation:
        query = select(ChatConversation).where(
            ChatConversation.id == chat_id,
            ChatConversation.owner_id == UUID(owner),
            ChatConversation.expires_at > datetime.now(UTC),
        )
        if lock:
            query = query.with_for_update()
        chat = await session.scalar(query)
        if chat is None:
            raise ChatNotFound
        return chat

    async def create(self, owner: str) -> ChatData:
        now = datetime.now(UTC)
        async with self.factory.begin() as session:
            record = ChatConversation(
                owner_id=UUID(owner), title="New chat", updated_at=now, expires_at=now + RETENTION
            )
            session.add(record)
            await session.flush()
            return ChatData(record.id, record.title, record.updated_at)

    async def list(self, owner: str) -> tuple[ChatData, ...]:
        async with self.factory() as session:
            rows = (
                await session.scalars(
                    select(ChatConversation)
                    .where(
                        ChatConversation.owner_id == UUID(owner),
                        ChatConversation.expires_at > datetime.now(UTC),
                    )
                    .order_by(ChatConversation.updated_at.desc(), ChatConversation.id)
                    .limit(100)
                )
            ).all()
            return tuple(ChatData(row.id, row.title, row.updated_at) for row in rows)

    async def _turn_data(self, session: AsyncSession, turn: ChatTurn) -> ChatTurnData:
        citation_rows = (
            await session.scalars(
                select(ChatCitation)
                .where(ChatCitation.turn_id == turn.id)
                .order_by(ChatCitation.ordinal)
            )
        ).all()
        repo = SourceRepository(session)
        citations = []
        for row in citation_rows:
            locator = Locator(
                page=row.page,
                section=row.section,
                sheet=row.sheet,
                table=row.table_name,
                row_start=row.row_start,
                row_end=row.row_end,
                column_start=row.column_start,
                column_end=row.column_end,
            )
            current = await repo.get_visible_citation(row.revision_id, row.segment_id)
            citations.append(
                ChatCitationData(
                    row.revision_id,
                    row.segment_id,
                    locator,
                    current is not None and current.locator == locator,
                )
            )
        return ChatTurnData(
            turn.id,
            turn.ordinal,
            turn.user_text,
            turn.assistant_text,
            turn.evidence_status,
            turn.status,
            tuple(citations),
            turn.rating,
            turn.feedback_comment,
        )

    async def rate(
        self, owner: str, chat_id: UUID, request_id: UUID,
        rating: str | None, comment: str | None,
    ) -> ChatTurnData:
        async with self.factory.begin() as session:
            await self._owned(session, owner, chat_id)
            turn = await session.get(ChatTurn, request_id, with_for_update=True)
            if turn is None or turn.conversation_id != chat_id:
                raise ChatNotFound
            if turn.status != "complete" or turn.assistant_text is None:
                raise ChatConflict("Only completed answers can be rated")
            turn.rating = rating
            turn.feedback_comment = comment
            turn.feedback_at = datetime.now(UTC) if rating is not None else None
            await session.flush()
            return await self._turn_data(session, turn)

    async def detail(self, owner: str, chat_id: UUID) -> ChatData:
        async with self.factory() as session:
            chat = await self._owned(session, owner, chat_id)
            turns = (
                await session.scalars(
                    select(ChatTurn)
                    .where(ChatTurn.conversation_id == chat_id)
                    .order_by(ChatTurn.ordinal)
                )
            ).all()
            return ChatData(
                chat.id,
                chat.title,
                chat.updated_at,
                tuple([await self._turn_data(session, turn) for turn in turns]),
            )

    async def delete(self, owner: str, chat_id: UUID) -> None:
        async with self.factory.begin() as session:
            chat = await self._owned(session, owner, chat_id, lock=True)
            await session.delete(chat)

    async def rename(self, owner: str, chat_id: UUID, title: str) -> ChatData:
        async with self.factory.begin() as session:
            chat = await self._owned(session, owner, chat_id, lock=True)
            chat.title = title
            chat.updated_at = datetime.now(UTC)
            await session.flush()
            return ChatData(chat.id, chat.title, chat.updated_at)

    async def claim(
        self, owner: str, chat_id: UUID, request_id: UUID, text: str, starter_id: str | None
    ) -> TurnClaim:
        now = datetime.now(UTC)
        async with self.factory.begin() as session:
            chat = await self._owned(session, owner, chat_id, lock=True)
            existing = await session.get(ChatTurn, request_id, with_for_update=True)
            if existing is not None:
                if (
                    existing.conversation_id != chat_id or existing.user_text != text
                    or existing.starter_id != starter_id
                ):
                    raise ChatConflict("Request ID already belongs to another message")
                if existing.status == "complete":
                    return TurnClaim(None, await self._turn_data(session, existing))
                if (
                    existing.status == "pending"
                    and existing.lease_until
                    and existing.lease_until > now
                ):
                    raise ChatConflict("Message is still processing")
                existing.status = "pending"
                existing.attempt += 1
                existing.lease_until = now + TURN_LEASE
                return TurnClaim(existing.attempt, None)
            pending = await session.scalar(
                select(ChatTurn.id).where(
                    ChatTurn.conversation_id == chat_id,
                    ChatTurn.status == "pending",
                )
            )
            if pending is not None:
                raise ChatConflict("Finish or retry the pending message first")
            highest = await session.scalar(
                select(func.max(ChatTurn.ordinal)).where(ChatTurn.conversation_id == chat_id)
            )
            session.add(
                ChatTurn(
                    id=request_id,
                    conversation_id=chat_id,
                    ordinal=(highest if highest is not None else -1) + 1,
                    user_text=text,
                    starter_id=starter_id,
                    status="pending",
                    attempt=1,
                    lease_until=now + TURN_LEASE,
                )
            )
            if chat.title == "New chat":
                chat.title = first_turn_title(text, starter_id)
            return TurnClaim(1, None)

    async def finish(
        self, owner: str, chat_id: UUID, request_id: UUID, attempt: int, answer: GeneratedAnswer
    ) -> ChatTurnData:
        now = datetime.now(UTC)
        async with self.factory.begin() as session:
            chat = await self._owned(session, owner, chat_id, lock=True)
            turn = await session.get(ChatTurn, request_id, with_for_update=True)
            if (
                turn is None
                or turn.conversation_id != chat_id
                or turn.status != "pending"
                or turn.attempt != attempt
            ):
                raise ChatConflict("Message attempt has changed")
            turn.status = "complete"
            turn.assistant_text = answer.text
            turn.evidence_status = answer.evidence_status
            turn.lease_until = None
            for ordinal, citation in enumerate(answer.citations):
                locator = citation.locator
                session.add(
                    ChatCitation(
                        turn_id=turn.id,
                        ordinal=ordinal,
                        revision_id=citation.revision_id,
                        segment_id=citation.segment_id,
                        page=locator.page,
                        section=locator.section,
                        sheet=locator.sheet,
                        table_name=locator.table,
                        row_start=locator.row_start,
                        row_end=locator.row_end,
                        column_start=locator.column_start,
                        column_end=locator.column_end,
                    )
                )
            chat.updated_at = now
            chat.expires_at = now + RETENTION
            await session.flush()
            return await self._turn_data(session, turn)

    async def fail(self, owner: str, chat_id: UUID, request_id: UUID, attempt: int) -> None:
        async with self.factory.begin() as session:
            await self._owned(session, owner, chat_id, lock=True)
            turn = await session.get(ChatTurn, request_id, with_for_update=True)
            if turn is not None and turn.conversation_id == chat_id and turn.attempt == attempt:
                turn.status = "failed"
                turn.lease_until = None

    async def purge_expired(self) -> int:
        async with self.factory.begin() as session:
            deleted = await session.scalars(
                delete(ChatConversation)
                .where(ChatConversation.expires_at <= datetime.now(UTC))
                .returning(ChatConversation.id)
            )
            return len(deleted.all())
