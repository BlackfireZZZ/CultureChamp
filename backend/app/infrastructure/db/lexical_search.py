"""PostgreSQL lexical baseline with decision filtering before rank and limit."""

import re
from typing import Any

from sqlalchemy import func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.sql.elements import ColumnElement

from app.application.retrieval import EvidenceSegment
from app.domain.sources import Locator
from app.infrastructure.db.source_models import (
    SourceDecision,
    SourceProcessing,
    SourceRevision,
    SourceSegment,
    SourceTag,
)

MAX_TERMS = 24
CONFIG: ColumnElement[Any] = literal_column("'russian'::regconfig")


def search_terms(query: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(re.findall(r"[^\W_]{3,}", query.casefold())))[:MAX_TERMS]


class SqlLexicalSearch:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self.factory = factory

    async def search(
        self,
        query: str,
        *,
        limit: int,
        region: str | None,
        people: str | None,
        for_provider: bool,
    ) -> tuple[EvidenceSegment, ...]:
        terms = search_terms(query)
        if not terms:
            return ()
        tsquery: ColumnElement[Any] = func.plainto_tsquery(CONFIG, terms[0])
        for term in terms[1:]:
            tsquery = tsquery.op("||")(func.plainto_tsquery(CONFIG, term))
        vector = func.to_tsvector(CONFIG, SourceSegment.text)
        score = func.ts_rank_cd(vector, tsquery).label("score")
        latest_event = (
            select(func.max(SourceDecision.event_id))
            .where(SourceDecision.revision_id == SourceRevision.id)
            .correlate(SourceRevision)
            .scalar_subquery()
        )
        statement = (
            select(SourceSegment, SourceRevision, score)
            .join(SourceRevision, SourceRevision.id == SourceSegment.revision_id)
            .join(SourceProcessing, SourceProcessing.revision_id == SourceRevision.id)
            .join(SourceDecision, SourceDecision.revision_id == SourceRevision.id)
            .where(
                SourceProcessing.state == "review_pending",
                SourceDecision.event_id == latest_event,
                SourceDecision.kind == "approve",
                SourceDecision.user_text.is_(True),
                SourceDecision.sensitivity_cleared.is_(True),
                SourceSegment.included.is_(True),
                vector.op("@@")(tsquery),
            )
        )
        if for_provider:
            statement = statement.where(SourceDecision.provider_transfer.is_(True))
        for kind, value in (("region", region), ("people", people)):
            if value is not None:
                tag_exists = (
                    select(SourceTag.id)
                    .where(
                        SourceTag.revision_id == SourceRevision.id,
                        SourceTag.kind == kind,
                        SourceTag.value == value,
                    )
                    .exists()
                )
                statement = statement.where(tag_exists)
        statement = statement.order_by(
            score.desc(), SourceRevision.id, SourceSegment.ordinal, SourceSegment.id
        ).limit(limit)
        async with self.factory() as session:
            rows = (await session.execute(statement)).all()
        return tuple(
            EvidenceSegment(
                revision_id=revision.id,
                segment_id=segment.id,
                title=revision.title,
                creator=revision.creator,
                locator=Locator(
                    page=segment.page,
                    section=segment.section,
                    sheet=segment.sheet,
                    table=segment.table_name,
                    row_start=segment.row_start,
                    row_end=segment.row_end,
                    column_start=segment.column_start,
                    column_end=segment.column_end,
                ),
                text=segment.text,
                score=float(rank),
            )
            for segment, revision, rank in rows
        )
