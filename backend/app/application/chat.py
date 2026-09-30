"""Private, retryable text conversations owned by the signed-in user."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.application.access import Actor, Role, require_role
from app.application.generation import GeneratedAnswer, GenerationService
from app.domain.sources import Locator


class ChatNotFound(Exception):
    pass


class ChatConflict(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ChatCitationData:
    revision_id: UUID
    segment_id: UUID
    locator: Locator
    available: bool


@dataclass(frozen=True, slots=True)
class ChatTurnData:
    request_id: UUID
    ordinal: int
    user_text: str
    assistant_text: str | None
    evidence_status: str | None
    status: str
    citations: tuple[ChatCitationData, ...]


@dataclass(frozen=True, slots=True)
class ChatData:
    id: UUID
    title: str
    updated_at: datetime
    turns: tuple[ChatTurnData, ...] = ()


@dataclass(frozen=True, slots=True)
class TurnClaim:
    attempt: int | None
    completed: ChatTurnData | None


class ChatPort(Protocol):
    async def create(self, owner: str) -> ChatData: ...

    async def list(self, owner: str) -> tuple[ChatData, ...]: ...

    async def detail(self, owner: str, chat_id: UUID) -> ChatData: ...

    async def delete(self, owner: str, chat_id: UUID) -> None: ...

    async def claim(self, owner: str, chat_id: UUID, request_id: UUID, text: str) -> TurnClaim: ...

    async def finish(
        self, owner: str, chat_id: UUID, request_id: UUID, attempt: int, answer: GeneratedAnswer
    ) -> ChatTurnData: ...

    async def fail(self, owner: str, chat_id: UUID, request_id: UUID, attempt: int) -> None: ...


class ChatService:
    def __init__(self, store: ChatPort, generation: GenerationService) -> None:
        self.store = store
        self.generation = generation

    async def create(self, actor: Actor) -> ChatData:
        require_role(actor, Role.USER)
        return await self.store.create(actor.subject_id)

    async def list(self, actor: Actor) -> tuple[ChatData, ...]:
        require_role(actor, Role.USER)
        return await self.store.list(actor.subject_id)

    async def detail(self, actor: Actor, chat_id: UUID) -> ChatData:
        require_role(actor, Role.USER)
        return await self.store.detail(actor.subject_id, chat_id)

    async def delete(self, actor: Actor, chat_id: UUID) -> None:
        require_role(actor, Role.USER)
        await self.store.delete(actor.subject_id, chat_id)

    async def send(self, actor: Actor, chat_id: UUID, request_id: UUID, text: str) -> ChatTurnData:
        require_role(actor, Role.USER)
        if not text.strip() or len(text) > 2_000:
            raise ValueError("Invalid chat message")
        claim = await self.store.claim(actor.subject_id, chat_id, request_id, text.strip())
        if claim.completed is not None:
            return claim.completed
        if claim.attempt is None:
            raise ChatConflict("Chat turn could not be claimed")
        try:
            answer = await self.generation.generate(actor, text.strip(), str(request_id))
        except Exception:
            await self.store.fail(actor.subject_id, chat_id, request_id, claim.attempt)
            raise
        return await self.store.finish(actor.subject_id, chat_id, request_id, claim.attempt, answer)
