"""Resolve citations through the current exact-revision decision."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.sources import Citation
from app.infrastructure.db.source_repository import SourceRepository


class SqlCitationResolver:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self.factory = factory

    async def resolve(self, revision_id: UUID, segment_id: UUID) -> Citation | None:
        async with self.factory() as session:
            return await SourceRepository(session).get_visible_citation(revision_id, segment_id)
