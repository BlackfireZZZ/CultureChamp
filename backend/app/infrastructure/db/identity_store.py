"""PostgreSQL adapter for invite-only accounts and hashed server sessions."""

import hashlib
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import case, delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.access import Actor, Role, Session
from app.application.identity import InvalidAccountInput, StoredAccount
from app.infrastructure.db.identity_models import (
    Account,
    AccountGrantEvent,
    LoginAttempt,
    LoginSession,
)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _account_record(account: Account) -> StoredAccount:
    return StoredAccount(
        id=account.id,
        username=account.username,
        password_hash=account.password_hash,
        role=Role(account.role),
        is_active=account.is_active,
    )


class SqlIdentityStore:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self.factory = factory

    async def get_account(self, username: str) -> StoredAccount | None:
        async with self.factory() as session:
            account = await session.scalar(select(Account).where(Account.username == username))
            return _account_record(account) if account is not None else None

    async def create_account(
        self, username: str, password_hash: str, role: Role, *, created_by: str | None = None
    ) -> StoredAccount:
        async with self.factory.begin() as session:
            account = Account(username=username, password_hash=password_hash, role=role.value)
            session.add(account)
            await session.flush()
            if created_by is not None:
                session.add(AccountGrantEvent(
                    actor_id=UUID(created_by), account_id=account.id, role=role.value
                ))
                await session.flush()
            return _account_record(account)

    async def bootstrap_admin(self, username: str, password_hash: str) -> StoredAccount:
        async with self.factory.begin() as session:
            await session.execute(select(func.pg_advisory_xact_lock(230013)))
            count = await session.scalar(select(func.count(Account.id)))
            if count:
                raise InvalidAccountInput("first admin already exists")
            account = Account(username=username, password_hash=password_hash, role=Role.ADMIN.value)
            session.add(account)
            await session.flush()
            return _account_record(account)

    async def reserve_login_attempt(self, principal: str, now: datetime) -> bool:
        principal_hash = _digest(principal)
        cutoff = now - timedelta(minutes=15)
        expired = LoginAttempt.window_start < cutoff
        statement = (
            insert(LoginAttempt)
            .values(principal_hash=principal_hash, window_start=now, attempts=1)
            .on_conflict_do_update(
                index_elements=[LoginAttempt.principal_hash],
                set_={
                    "window_start": case((expired, now), else_=LoginAttempt.window_start),
                    "attempts": case((expired, 1), else_=LoginAttempt.attempts + 1),
                },
            )
            .returning(LoginAttempt.attempts)
        )
        async with self.factory.begin() as session:
            attempts = await session.scalar(statement)
            return attempts is not None and attempts <= 5

    async def reset_login_attempts(self, principal: str) -> None:
        async with self.factory.begin() as session:
            await session.execute(
                delete(LoginAttempt).where(LoginAttempt.principal_hash == _digest(principal))
            )

    async def create_session(self, token: str, session_value: Session) -> None:
        async with self.factory.begin() as session:
            session.add(
                LoginSession(
                    token_hash=_digest(token),
                    account_id=UUID(session_value.actor.subject_id),
                    csrf_token=session_value.csrf_token,
                    issued_at=session_value.issued_at,
                    expires_at=session_value.expires_at,
                )
            )

    async def find(self, token: str) -> Session | None:
        async with self.factory() as session:
            result = await session.execute(
                select(LoginSession, Account)
                .join(Account, Account.id == LoginSession.account_id)
                .where(LoginSession.token_hash == _digest(token))
            )
            row = result.first()
            if row is None:
                return None
            stored_session, account = row
            if stored_session.revoked_at is not None or not account.is_active:
                return None
            return Session(
                actor=Actor(str(account.id), Role(account.role), account.username),
                issued_at=stored_session.issued_at,
                expires_at=stored_session.expires_at,
                csrf_token=stored_session.csrf_token,
            )

    async def revoke_session(self, token: str) -> None:
        async with self.factory.begin() as session:
            await session.execute(
                update(LoginSession)
                .where(LoginSession.token_hash == _digest(token))
                .values(revoked_at=datetime.now(UTC))
            )
