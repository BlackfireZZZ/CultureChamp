"""PostgreSQL-backed daily model limits shared across API processes."""

from datetime import UTC, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.db.chat_models import GenerationAttempt, GenerationReservation
from app.infrastructure.model.gateway import ModelResult

USER_DAILY_LIMIT = 20
GLOBAL_DAILY_LIMIT = 100


class SqlModelQuota:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self.factory = factory

    async def reserve(self, subject_id: str, idempotency_key: str) -> bool:
        now = datetime.now(UTC)
        day_start = datetime.combine(now.date(), time.min, tzinfo=UTC)
        subject = UUID(subject_id)
        key = UUID(idempotency_key)
        async with self.factory.begin() as session:
            await session.execute(text("SELECT pg_advisory_xact_lock(746932)"))
            existing = await session.get(GenerationReservation, key, with_for_update=True)
            if existing is not None and (
                existing.subject_id != subject
                or existing.status == "done"
                or (existing.status == "active" and existing.lease_until > now)
            ):
                return False
            active = await session.scalar(
                select(func.count())
                .select_from(GenerationReservation)
                .where(
                    GenerationReservation.subject_id == subject,
                    GenerationReservation.status == "active",
                    GenerationReservation.lease_until > now,
                )
            )
            if active:
                return False
            user_count = await session.scalar(
                select(func.count())
                .select_from(GenerationAttempt)
                .where(
                    GenerationAttempt.subject_id == subject,
                    GenerationAttempt.created_at >= day_start,
                )
            )
            global_count = await session.scalar(
                select(func.count())
                .select_from(GenerationAttempt)
                .where(GenerationAttempt.created_at >= day_start)
            )
            if (user_count or 0) >= USER_DAILY_LIMIT or (global_count or 0) >= GLOBAL_DAILY_LIMIT:
                return False
            if existing is not None:
                existing.status = "active"
                existing.lease_until = now + timedelta(seconds=45)
                existing.input_tokens = None
                existing.output_tokens = None
            else:
                session.add(
                    GenerationReservation(
                        id=key,
                        subject_id=subject,
                        status="active",
                        created_at=now,
                        lease_until=now + timedelta(seconds=45),
                    )
                )
                await session.flush()
            session.add(GenerationAttempt(reservation_id=key, subject_id=subject, created_at=now))
            return True

    async def finish(
        self, subject_id: str, idempotency_key: str, result: ModelResult | None,
        *, accepted: bool = True,
    ) -> None:
        async with self.factory.begin() as session:
            record = await session.get(
                GenerationReservation, UUID(idempotency_key), with_for_update=True
            )
            if record is None or record.subject_id != UUID(subject_id):
                return
            record.status = "done" if accepted and result is not None else "failed"
            record.input_tokens = result.input_tokens if result is not None else None
            record.output_tokens = result.output_tokens if result is not None else None
            attempt = await session.scalar(
                select(GenerationAttempt)
                .where(GenerationAttempt.reservation_id == record.id)
                .order_by(GenerationAttempt.id.desc())
                .limit(1)
                .with_for_update()
            )
            if attempt is not None:
                attempt.accepted = accepted and result is not None
                attempt.input_tokens = record.input_tokens
                attempt.output_tokens = record.output_tokens

    async def purge_old(self) -> int:
        cutoff = datetime.now(UTC) - timedelta(days=30)
        async with self.factory.begin() as session:
            deleted = await session.scalars(
                delete(GenerationReservation)
                .where(GenerationReservation.created_at < cutoff)
                .returning(GenerationReservation.id)
            )
            return len(deleted.all())
