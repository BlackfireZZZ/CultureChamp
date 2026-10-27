"""SQL-authorized dense/lexical union with a final post-rerank rights check."""

import asyncio
import math
from collections.abc import Sequence
from dataclasses import replace
from typing import Protocol
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.retrieval import EvidenceSegment
from app.domain.sources import Locator
from app.infrastructure.db.source_models import (
    SourceDecision,
    SourceProcessing,
    SourceRevision,
    SourceSegment,
    SourceTag,
    SourceVectorIndex,
)
from app.infrastructure.vector.local_retrieval import LocalCrossEncoderReranker, RussianBM25
from app.infrastructure.vector.text_vectors import MODEL_ID, QdrantTextIndex, VectorUnavailable

CANDIDATE_DEPTH = 50


class Reranker(Protocol):
    async def rerank(self, query: str, passages: Sequence[str]) -> list[float]: ...


def _scope(
    statement: Select[tuple[SourceRevision]],
    *,
    region: str | None,
    people: str | None,
    for_provider: bool,
) -> Select[tuple[SourceRevision]]:
    latest = (select(func.max(SourceDecision.event_id))
              .where(SourceDecision.revision_id == SourceRevision.id)
              .correlate(SourceRevision).scalar_subquery())
    statement = statement.join(SourceProcessing).join(SourceDecision).where(
        SourceProcessing.state == "review_pending",
        SourceDecision.event_id == latest,
        SourceDecision.kind == "approve",
        SourceDecision.user_text.is_(True),
        SourceDecision.sensitivity_cleared.is_(True),
    )
    if for_provider:
        statement = statement.where(SourceDecision.provider_transfer.is_(True))
    for kind, value in (("region", region), ("people", people)):
        if value is not None:
            statement = statement.where(select(SourceTag.id).where(
                SourceTag.revision_id == SourceRevision.id,
                SourceTag.kind == kind, SourceTag.value == value,
            ).exists())
    return statement


class SqlGovernedHybridSearch:
    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        index: QdrantTextIndex,
        reranker: Reranker | None = None,
        lexical: RussianBM25 | None = None,
    ) -> None:
        self.factory = factory
        self.index = index
        self.reranker = reranker or LocalCrossEncoderReranker()
        self.lexical = lexical or RussianBM25()

    async def search(
        self, query: str, *, limit: int, region: str | None,
        people: str | None, for_provider: bool,
    ) -> tuple[EvidenceSegment, ...]:
        scoped = _scope(select(SourceRevision), region=region, people=people,
                        for_provider=for_provider)
        eligible = scoped.join(SourceVectorIndex).where(SourceVectorIndex.model_id == MODEL_ID)
        pending = scoped.outerjoin(SourceVectorIndex).where(
            (SourceVectorIndex.revision_id.is_(None)) | (SourceVectorIndex.model_id != MODEL_ID)
        ).limit(1)
        async with self.factory() as session:
            revisions = (await session.scalars(eligible)).all()
            has_pending = await session.scalar(pending) is not None
            allowed = {revision.id: revision for revision in revisions}
            segments = (await session.scalars(select(SourceSegment).where(
                SourceSegment.revision_id.in_(allowed), SourceSegment.included.is_(True)
            ).order_by(SourceSegment.revision_id, SourceSegment.ordinal, SourceSegment.id))).all()
        if not allowed:
            return self._empty(has_pending)
        # Excluded stale points must not consume dense candidate slots either.
        dense = await self.index.query(
            query, CANDIDATE_DEPTH, allowed_revision_ids=list(allowed),
            allowed_segment_ids=[segment.id for segment in segments],
        )
        if not dense and segments:
            raise VectorUnavailable("Approved evidence index is incomplete")
        lexical_ids = await asyncio.to_thread(
            self.lexical.rank, query, [(segment.id, segment.text) for segment in segments],
            CANDIDATE_DEPTH,
        )
        by_id = {segment.id: segment for segment in segments}
        candidates = list(dict.fromkeys([sid for sid, _ in dense] + lexical_ids))
        candidates = [sid for sid in candidates if sid in by_id]
        if not candidates:
            return self._empty(has_pending)
        scores = await self.reranker.rerank(query, [by_id[sid].text for sid in candidates])
        if len(scores) != len(candidates) or not all(math.isfinite(s) for s in scores):
            raise VectorUnavailable("Invalid passage reranking result")
        order = sorted(range(len(candidates)), key=lambda i: (-scores[i], i))
        # Reranking can be slow. Re-evaluate current decisions, tags, index generation
        # and segment inclusion after it, instead of trusting the first SQL snapshot.
        current = _scope(select(SourceRevision), region=region, people=people,
                         for_provider=for_provider).join(SourceVectorIndex).where(
                             SourceRevision.id.in_(allowed),
                             SourceVectorIndex.model_id == MODEL_ID,
                         )
        async with self.factory() as session:
            visible_revisions = {r.id: r for r in (await session.scalars(current)).all()}
            visible_ids = set((await session.scalars(select(SourceSegment.id).where(
                SourceSegment.id.in_(candidates), SourceSegment.included.is_(True),
                SourceSegment.revision_id.in_(visible_revisions),
            ))).all())
            tags = (await session.scalars(select(SourceTag).where(
                SourceTag.revision_id.in_(visible_revisions),
                SourceTag.kind.in_(("region", "people", "period")),
            ).order_by(SourceTag.kind, SourceTag.value))).all()
        tags_by_revision: dict[UUID, list[tuple[str, str]]] = {}
        for tag in tags:
            tags_by_revision.setdefault(tag.revision_id, []).append((tag.kind, tag.value))
        found = []
        for position in order:
            sid = candidates[position]
            if sid not in visible_ids:
                continue
            segment = by_id[sid]
            revision = visible_revisions[segment.revision_id]
            item = EvidenceSegment(
                revision.id, sid, revision.title, revision.creator,
                Locator(page=segment.page, section=segment.section, sheet=segment.sheet,
                        table=segment.table_name, row_start=segment.row_start,
                        row_end=segment.row_end, column_start=segment.column_start,
                        column_end=segment.column_end),
                segment.text, scores[position],
            )
            found.append(replace(item, context_tags=tuple(tags_by_revision.get(revision.id, ()))))
            if len(found) == limit:
                break
        return tuple(found) if found else self._empty(has_pending)

    @staticmethod
    def _empty(has_pending: bool) -> tuple[EvidenceSegment, ...]:
        if has_pending:
            raise VectorUnavailable("Approved evidence is awaiting indexing")
        return ()
