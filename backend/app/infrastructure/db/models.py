"""Import ORM tables for Alembic metadata registration."""

from app.infrastructure.db.identity_models import Account, LoginAttempt, LoginSession  # noqa: F401
from app.infrastructure.db.source_models import (  # noqa: F401
    Source,
    SourceDecision,
    SourceRevision,
    SourceSegment,
    SourceTag,
)
