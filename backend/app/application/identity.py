"""Invite-only account and session use cases."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from typing import Protocol
from uuid import UUID

from app.application.access import Actor, Role, Session, require_role

USERNAME_PATTERN = re.compile(r"[a-z][a-z0-9_.-]{2,49}\Z")


class InvalidCredentials(Exception):
    pass


class LoginThrottled(Exception):
    pass


class InvalidAccountInput(Exception):
    pass


@dataclass(frozen=True)
class StoredAccount:
    id: UUID
    username: str
    password_hash: str
    role: Role
    is_active: bool


@dataclass(frozen=True)
class LoginResult:
    token: str
    session: Session


class IdentityStore(Protocol):
    async def get_account(self, username: str) -> StoredAccount | None: ...

    async def create_account(
        self, username: str, password_hash: str, role: Role, *, created_by: str | None = None
    ) -> StoredAccount: ...

    async def bootstrap_admin(self, username: str, password_hash: str) -> StoredAccount: ...

    async def reserve_login_attempt(self, principal: str, now: datetime) -> bool: ...

    async def reset_login_attempts(self, principal: str) -> None: ...

    async def create_session(self, token: str, session: Session) -> None: ...

    async def revoke_session(self, token: str) -> None: ...


class PasswordCodec(Protocol):
    async def hash(self, password: str) -> str: ...

    async def verify(self, password_hash: str, password: str) -> bool: ...


def normalize_username(username: str) -> str:
    normalized = username.strip().lower()
    if not USERNAME_PATTERN.fullmatch(normalized):
        raise InvalidAccountInput("invalid username")
    return normalized


def validate_password(password: str) -> None:
    if not 12 <= len(password) <= 128:
        raise InvalidAccountInput("password length must be 12–128 characters")


class IdentityService:
    def __init__(self, store: IdentityStore, codec: PasswordCodec, dummy_hash: str) -> None:
        self.store = store
        self.codec = codec
        self.dummy_hash = dummy_hash

    async def bootstrap_admin(self, username: str, password: str) -> StoredAccount:
        normalized = normalize_username(username)
        validate_password(password)
        return await self.store.bootstrap_admin(normalized, await self.codec.hash(password))

    async def create_account(
        self, actor: Actor, username: str, password: str, role: Role
    ) -> StoredAccount:
        require_role(actor, Role.ADMIN)
        normalized = normalize_username(username)
        validate_password(password)
        return await self.store.create_account(
            normalized, await self.codec.hash(password), role,
            created_by=actor.subject_id,
        )

    async def login(self, username: str, password: str) -> LoginResult:
        try:
            normalized = normalize_username(username)
        except InvalidAccountInput as exc:
            raise InvalidCredentials from exc
        now = datetime.now(UTC)
        if not await self.store.reserve_login_attempt(normalized, now):
            raise LoginThrottled
        account = await self.store.get_account(normalized)
        password_hash = account.password_hash if account is not None else self.dummy_hash
        matches = await self.codec.verify(password_hash, password)
        if account is None or not account.is_active or not matches:
            raise InvalidCredentials
        await self.store.reset_login_attempts(normalized)
        session = Session(
            actor=Actor(str(account.id), account.role, account.username),
            issued_at=now,
            expires_at=now + timedelta(hours=12),
            csrf_token=token_urlsafe(32),
        )
        token = token_urlsafe(32)
        await self.store.create_session(token, session)
        return LoginResult(token, session)

    async def logout(self, token: str) -> None:
        await self.store.revoke_session(token)
