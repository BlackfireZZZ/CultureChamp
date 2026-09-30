"""Import ORM tables for Alembic metadata registration."""

from app.infrastructure.db.chat_models import (  # noqa: F401
    ChatCitation,
    ChatConversation,
    ChatTurn,
    GenerationAttempt,
    GenerationReservation,
)
from app.infrastructure.db.identity_models import (  # noqa: F401
    Account,
    AccountGrantEvent,
    LoginAttempt,
    LoginSession,
)
from app.infrastructure.db.source_models import (  # noqa: F401
    Source,
    SourceDecision,
    SourceMetadataEvent,
    SourceProcessing,
    SourceRevision,
    SourceSegment,
    SourceTag,
    SourceVectorIndex,
)
