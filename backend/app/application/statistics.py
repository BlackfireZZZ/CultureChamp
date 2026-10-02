"""Aggregate request metadata for administrator reporting."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from app.application.access import Actor, Role, require_role


@dataclass(frozen=True, slots=True)
class DailyCount:
    date: date
    count: int


@dataclass(frozen=True, slots=True)
class StarterCount:
    starter_id: str
    count: int


@dataclass(frozen=True, slots=True)
class RequestStatistics:
    period_start: date
    period_end: date
    daily_requests: tuple[DailyCount, ...]
    starter_requests: tuple[StarterCount, ...]
    rated_up: int
    rated_down: int
    feedback: tuple["FeedbackItem", ...]


@dataclass(frozen=True, slots=True)
class FeedbackItem:
    request_id: str
    rated_at: datetime
    rating: str
    comment: str | None
    evidence_status: str | None
    starter_id: str | None


class StatisticsPort(Protocol):
    async def read(self, days: int) -> RequestStatistics: ...


class StatisticsService:
    def __init__(self, store: StatisticsPort) -> None:
        self.store = store

    async def read(self, actor: Actor, days: int) -> RequestStatistics:
        require_role(actor, Role.ADMIN)
        if not 1 <= days <= 90:
            raise ValueError("Invalid statistics period")
        return await self.store.read(days)
