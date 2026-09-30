from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Protocol


class Role(StrEnum):
    USER = "user"
    ADMIN = "admin"


@dataclass(frozen=True)
class Actor:
    subject_id: str
    role: Role
    username: str | None = None


@dataclass(frozen=True)
class Session:
    actor: Actor
    issued_at: datetime
    expires_at: datetime
    csrf_token: str

    def is_valid(self, now: datetime | None = None) -> bool:
        current = now or datetime.now(UTC)
        return (
            self.issued_at.tzinfo is not None
            and self.expires_at.tzinfo is not None
            and self.issued_at <= current < self.expires_at
            and self.expires_at - self.issued_at <= timedelta(hours=12)
        )


class SessionStore(Protocol):
    async def find(self, token: str) -> Session | None: ...


class AccessDenied(Exception):
    pass


class HiddenResource(Exception):
    pass


def require_role(actor: Actor, role: Role) -> None:
    if actor.role != role:
        raise AccessDenied


def require_owner(actor: Actor, owner_subject_id: str) -> None:
    if actor.subject_id != owner_subject_id:
        raise HiddenResource


def require_visible_revision(
    actor: Actor, *, approved: bool, revoked: bool, rights_permitted: bool
) -> None:
    if actor.role == Role.ADMIN:
        return
    if not approved or revoked or not rights_permitted:
        raise HiddenResource
