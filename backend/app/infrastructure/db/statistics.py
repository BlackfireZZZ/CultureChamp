"""Content-free aggregates over retained chat requests."""

from datetime import UTC, datetime, time, timedelta

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.statistics import DailyCount, RequestStatistics, StarterCount
from app.infrastructure.db.chat_models import ChatTurn


class SqlStatisticsStore:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self.factory = factory

    async def read(self, days: int) -> RequestStatistics:
        end = datetime.now(UTC).date()
        start = end - timedelta(days=days - 1)
        lower = datetime.combine(start, time.min, UTC)
        upper = datetime.combine(end + timedelta(days=1), time.min, UTC)
        window = (ChatTurn.created_at >= lower, ChatTurn.created_at < upper)
        async with self.factory() as session:
            daily = (
                await session.execute(
                    select(cast(ChatTurn.created_at, Date), func.count())
                    .where(*window)
                    .group_by(cast(ChatTurn.created_at, Date))
                    .order_by(cast(ChatTurn.created_at, Date))
                )
            ).all()
            starters = (
                await session.execute(
                    select(ChatTurn.starter_id, func.count())
                    .where(*window, ChatTurn.starter_id.is_not(None))
                    .group_by(ChatTurn.starter_id)
                    .order_by(ChatTurn.starter_id)
                )
            ).all()
        return RequestStatistics(
            start, end,
            tuple(DailyCount(day, count) for day, count in daily),
            tuple(StarterCount(starter_id, count) for starter_id, count in starters),
        )
