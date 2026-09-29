"""Import ORM tables for Alembic metadata registration."""

from app.infrastructure.db.source_models import (  # noqa: F401
    Source,
    SourceDecision,
    SourceRevision,
    SourceSegment,
    SourceTag,
)
