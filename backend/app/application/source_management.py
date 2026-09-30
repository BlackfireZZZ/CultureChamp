"""Governed candidate intake and exact-revision material use cases."""

from dataclasses import dataclass
from typing import BinaryIO, Protocol
from urllib.parse import urlsplit
from uuid import UUID

from app.application.access import Actor, Role, require_role
from app.domain.sources import Locator


class SourceNotFound(Exception):
    pass


class SourceConflict(Exception):
    pass


class SourceInputError(Exception):
    pass


@dataclass(frozen=True)
class SegmentData:
    segment_id: UUID
    locator: Locator
    text: str


@dataclass(frozen=True)
class TagData:
    kind: str
    value: str


@dataclass(frozen=True)
class MaterialFilters:
    q: str | None = None
    region: str | None = None
    people: str | None = None
    period: str | None = None
    media_type: str | None = None


@dataclass(frozen=True)
class MaterialData:
    revision_id: UUID
    title: str
    creator: str | None
    origin_url: str
    rights_usage_note: str | None
    media_type: str
    description: str | None = None
    tags: tuple[TagData, ...] = ()
    segments: tuple[SegmentData, ...] = ()
    original_available: bool = False


@dataclass(frozen=True)
class AdminRevisionData:
    material: MaterialData
    source_id: UUID
    status: str
    error_code: str | None
    decision: str | None
    sha256: str


@dataclass(frozen=True)
class AdminSourceData:
    source_id: UUID
    revision_id: UUID
    title: str
    origin_url: str
    status: str
    decision: str | None


@dataclass(frozen=True)
class IntakeData:
    source_id: UUID
    revision_id: UUID
    status: str


@dataclass(frozen=True)
class OriginalData:
    content: bytes
    filename: str
    media_type: str


@dataclass(frozen=True)
class ApprovalData:
    reason: str
    evidence_url: str
    user_text: bool
    original_file: bool
    provider_transfer: bool
    sensitivity_cleared: bool


class SourceGateway(Protocol):
    async def upload(
        self,
        *,
        origin_url: str,
        title: str,
        description: str | None,
        creator: str | None,
        rights_note: str | None,
        source_id: UUID | None,
        stream: BinaryIO,
        filename: str,
        media_type: str,
        tags: tuple[TagData, ...],
    ) -> IntakeData: ...

    async def admin_detail(self, revision_id: UUID) -> AdminRevisionData: ...

    async def admin_original(self, revision_id: UUID) -> OriginalData: ...

    async def admin_list(
        self, *, status: str | None, decision: str | None, limit: int
    ) -> list[AdminSourceData]: ...

    async def approve(self, revision_id: UUID, reviewer_id: str, data: ApprovalData) -> None: ...

    async def revoke(self, revision_id: UUID, reviewer_id: str, reason: str) -> None: ...

    async def retry(self, revision_id: UUID) -> None: ...

    async def visible_list(self, filters: MaterialFilters) -> list[MaterialData]: ...

    async def visible_detail(self, revision_id: UUID) -> MaterialData: ...

    async def visible_original(self, revision_id: UUID) -> OriginalData: ...


class SourceService:
    def __init__(self, gateway: SourceGateway) -> None:
        self.gateway = gateway

    async def upload(
        self,
        actor: Actor,
        *,
        origin_url: str,
        title: str,
        description: str | None,
        creator: str | None,
        rights_note: str | None,
        source_id: UUID | None,
        stream: BinaryIO,
        filename: str,
        media_type: str,
        tags: list[str] | None = None,
    ) -> IntakeData:
        require_role(actor, Role.ADMIN)
        if description is not None:
            description = description.strip() or None
            if description is not None and len(description) > 500:
                raise SourceInputError("Description is too long")
        parsed_tags = []
        if len(tags or []) > 20:
            raise SourceInputError("Too many tags")
        for item in tags or []:
            kind, separator, value = item.partition(":")
            if (
                not separator
                or kind not in {"region", "people", "period", "topic", "sensitivity"}
                or not value.strip()
                or len(value) > 100
            ):
                raise SourceInputError("Invalid source tag")
            parsed_tags.append(TagData(kind, value.strip()))
        return await self.gateway.upload(
            origin_url=origin_url,
            title=title,
            description=description,
            creator=creator,
            rights_note=rights_note,
            source_id=source_id,
            stream=stream,
            filename=filename,
            media_type=media_type,
            tags=tuple(parsed_tags),
        )

    async def admin_detail(self, actor: Actor, revision_id: UUID) -> AdminRevisionData:
        require_role(actor, Role.ADMIN)
        return await self.gateway.admin_detail(revision_id)

    async def admin_original(self, actor: Actor, revision_id: UUID) -> OriginalData:
        require_role(actor, Role.ADMIN)
        return await self.gateway.admin_original(revision_id)

    async def admin_list(
        self,
        actor: Actor,
        *,
        status: str | None = None,
        decision: str | None = None,
        limit: int = 100,
    ) -> list[AdminSourceData]:
        require_role(actor, Role.ADMIN)
        return await self.gateway.admin_list(status=status, decision=decision, limit=limit)

    async def approve(
        self, actor: Actor, revision_id: UUID, data: ApprovalData
    ) -> AdminRevisionData:
        require_role(actor, Role.ADMIN)
        if not data.user_text or not data.sensitivity_cleared:
            raise SourceInputError("User text rights and sensitivity clearance required")
        evidence = urlsplit(data.evidence_url)
        if evidence.scheme != "https" or not evidence.hostname:
            raise SourceInputError("HTTPS rights evidence URL required")
        await self.gateway.approve(revision_id, actor.subject_id, data)
        return await self.gateway.admin_detail(revision_id)

    async def revoke(self, actor: Actor, revision_id: UUID, reason: str) -> AdminRevisionData:
        require_role(actor, Role.ADMIN)
        await self.gateway.revoke(revision_id, actor.subject_id, reason)
        return await self.gateway.admin_detail(revision_id)

    async def retry(self, actor: Actor, revision_id: UUID) -> AdminRevisionData:
        require_role(actor, Role.ADMIN)
        await self.gateway.retry(revision_id)
        return await self.gateway.admin_detail(revision_id)

    async def visible_list(
        self, actor: Actor, filters: MaterialFilters | None = None
    ) -> list[MaterialData]:
        require_role(actor, Role.USER)
        return await self.gateway.visible_list(filters or MaterialFilters())

    async def visible_detail(self, actor: Actor, revision_id: UUID) -> MaterialData:
        require_role(actor, Role.USER)
        return await self.gateway.visible_detail(revision_id)

    async def visible_original(self, actor: Actor, revision_id: UUID) -> OriginalData:
        require_role(actor, Role.USER)
        return await self.gateway.visible_original(revision_id)
