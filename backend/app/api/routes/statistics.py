"""Administrator-only request counts without prompt inspection."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.auth import current_admin
from app.application.access import Actor
from app.application.statistics import StatisticsService
from app.infrastructure.db.session import session_factory
from app.infrastructure.db.statistics import SqlStatisticsStore

router = APIRouter(prefix="/admin/request-statistics", tags=["admin"])


class DailyCountView(BaseModel):
    date: date
    count: int


class StarterCountView(BaseModel):
    starter_id: str
    count: int


class RequestStatisticsView(BaseModel):
    period_start: date
    period_end: date
    daily_requests: list[DailyCountView]
    starter_requests: list[StarterCountView]


def get_statistics_service(request: Request) -> StatisticsService:
    factory: async_sessionmaker[AsyncSession] = getattr(
        request.app.state, "source_session_factory", session_factory
    )
    return StatisticsService(SqlStatisticsStore(factory))


@router.get("", response_model=RequestStatisticsView)
async def request_statistics(
    response: Response,
    actor: Annotated[Actor, Depends(current_admin)],
    service: Annotated[StatisticsService, Depends(get_statistics_service)],
    days: Annotated[int, Query(ge=1, le=90)] = 30,
) -> RequestStatisticsView:
    result = await service.read(actor, days)
    response.headers["Cache-Control"] = "no-store"
    return RequestStatisticsView(
        period_start=result.period_start,
        period_end=result.period_end,
        daily_requests=[DailyCountView(date=item.date, count=item.count)
                        for item in result.daily_requests],
        starter_requests=[StarterCountView(starter_id=item.starter_id, count=item.count)
                          for item in result.starter_requests],
    )
