"""User-scoped retrieval of exact, source-located evidence."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.application.access import Actor, Role, require_role
from app.domain.sources import Locator


@dataclass(frozen=True, slots=True)
class EvidenceSegment:
    revision_id: UUID
    segment_id: UUID
    title: str
    creator: str | None
    locator: Locator
    text: str
    score: float
    context_tags: tuple[tuple[str, str], ...] = ()


class SearchPort(Protocol):
    async def search(
        self,
        query: str,
        *,
        limit: int,
        region: str | None,
        people: str | None,
        for_provider: bool,
    ) -> tuple[EvidenceSegment, ...]: ...


class RetrievalService:
    def __init__(self, search_port: SearchPort) -> None:
        self.search_port = search_port

    async def search(
        self,
        actor: Actor,
        query: str,
        *,
        limit: int = 5,
        region: str | None = None,
        people: str | None = None,
        for_provider: bool = False,
    ) -> tuple[EvidenceSegment, ...]:
        require_role(actor, Role.USER)
        if not query.strip() or len(query) > 2_000 or not 1 <= limit <= 10:
            raise ValueError("Invalid search request")
        if any(
            value is not None and (not value.strip() or len(value) > 100)
            for value in (region, people)
        ):
            raise ValueError("Invalid metadata filter")
        return await self.search_port.search(
            query,
            limit=limit,
            region=region,
            people=people,
            for_provider=for_provider,
        )
