"""Launch the durable candidate PDF extraction worker."""

import asyncio
from pathlib import Path

from app.core.config import settings
from app.infrastructure.db.session import engine, session_factory
from app.infrastructure.ingestion.processing import run_worker


async def main() -> None:
    try:
        await run_worker(session_factory, Path(settings.source_storage_root))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
