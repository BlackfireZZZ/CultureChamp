"""Governed candidate intake and exact-revision material use cases."""

from dataclasses import dataclass
from datetime import datetime
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
    included: bool = True


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
class AdminInventoryFilters:
    status: str | None = None
    decision: str | None = None
    q: str | None = None
    media_type: str | None = None
    tag_kind: str | None = None
    tag_value: str | None = None
    limit: int = 100


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
    metadata_version: int
    segment_review_version: int = 0


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


@dataclass(frozen=True)
class MetadataAmendment:
    expected_version: int
    reason: str
    description: str | None
    tags: tuple[TagData, ...]


@dataclass(frozen=True)
class MetadataEventData:
    version: int
    reviewer_id: str
    reason: str
    description: str | None
    tags: tuple[TagData, ...]
    changed_at: datetime


@dataclass(frozen=True)
class SegmentReview:
    expected_version: int
    reason: str
    excluded_segment_ids: tuple[UUID, ...]


@dataclass(frozen=True)
class SegmentReviewEventData:
    version: int
    reviewer_id: str
    reason: str
    excluded_segment_ids: tuple[UUID, ...]
    changed_at: datetime


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

    async def amend_metadata(
        self, revision_id: UUID, reviewer_id: str, data: MetadataAmendment
    ) -> AdminRevisionData: ...

    async def metadata_history(self, revision_id: UUID) -> list[MetadataEventData]: ...

    async def review_segments(
        self, revision_id: UUID, reviewer_id: str, data: SegmentReview
    ) -> AdminRevisionData: ...

    async def segment_history(self, revision_id: UUID) -> list[SegmentReviewEventData]: ...

    async def admin_list(self, filters: AdminInventoryFilters) -> list[AdminSourceData]: ...

    async def approve(self, revision_id: UUID, reviewer_id: str, data: ApprovalData) -> None: ...

    async def revoke(self, revision_id: UUID, reviewer_id: str, reason: str) -> None: ...

    async def retry(self, revision_id: UUID) -> None: ...

    async def visible_list(self, filters: MaterialFilters) -> list[MaterialData]: ...

    async def visible_detail(self, revision_id: UUID) -> MaterialData: ...

    async def visible_original(self, revision_id: UUID) -> OriginalData: ...


class SourceService:
    def __init__(self, gateway: SourceGateway, *, local_test_mode: bool = False) -> None:
        self.gateway = gateway
        self.local_test_mode = local_test_mode

    @staticmethod
    def _parse_tags(items: list[str]) -> tuple[TagData, ...]:
        if len(items) > 20:
            raise SourceInputError("Too many tags")
        parsed = []
        for item in items:
            kind, separator, value = item.partition(":")
            if (
                not separator
                or kind not in {"region", "people", "period", "topic", "sensitivity"}
                or not value.strip()
                or len(value.strip()) > 100
            ):
                raise SourceInputError("Invalid source tag")
            parsed.append(TagData(kind, value.strip()))
        if len({(item.kind, item.value) for item in parsed}) != len(parsed):
            raise SourceInputError("Duplicate source tag")
        return tuple(parsed)

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
        try:
            origin = urlsplit(origin_url)
            valid_origin = (
                origin.scheme in {"http", "https"}
                and bool(origin.hostname)
                and origin.username is None
                and origin.password is None
                and not any(char.isspace() or ord(char) < 32 for char in origin_url)
            )
        except ValueError:
            valid_origin = False
        if not valid_origin:
            raise SourceInputError("HTTP(S) source URL required")
        if description is not None:
            description = description.strip() or None
            if description is not None and len(description) > 500:
                raise SourceInputError("Description is too long")
        parsed_tags = self._parse_tags(tags or [])
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
            tags=parsed_tags,
        )

    async def admin_detail(self, actor: Actor, revision_id: UUID) -> AdminRevisionData:
        require_role(actor, Role.ADMIN)
        return await self.gateway.admin_detail(revision_id)

    async def admin_original(self, actor: Actor, revision_id: UUID) -> OriginalData:
        require_role(actor, Role.ADMIN)
        return await self.gateway.admin_original(revision_id)

    async def amend_metadata(
        self, actor: Actor, revision_id: UUID, data: MetadataAmendment
    ) -> AdminRevisionData:
        require_role(actor, Role.ADMIN)
        description = data.description.strip() if data.description is not None else None
        if description is not None and len(description) > 500:
            raise SourceInputError("Description is too long")
        tags = self._parse_tags([f"{item.kind}:{item.value}" for item in data.tags])
        if len(data.reason.strip()) < 10 or data.expected_version < 0:
            raise SourceInputError("Invalid metadata amendment")
        return await self.gateway.amend_metadata(
            revision_id, actor.subject_id,
            MetadataAmendment(
                data.expected_version, data.reason.strip(), description or None, tags
            ),
        )

    async def metadata_history(
        self, actor: Actor, revision_id: UUID
    ) -> list[MetadataEventData]:
        require_role(actor, Role.ADMIN)
        return await self.gateway.metadata_history(revision_id)

    async def review_segments(
        self, actor: Actor, revision_id: UUID, data: SegmentReview
    ) -> AdminRevisionData:
        require_role(actor, Role.ADMIN)
        if (
            data.expected_version < 0
            or not 10 <= len(data.reason.strip()) <= 2000
            or len(set(data.excluded_segment_ids)) != len(data.excluded_segment_ids)
        ):
            raise SourceInputError("Invalid segment review")
        return await self.gateway.review_segments(
            revision_id, actor.subject_id,
            SegmentReview(data.expected_version, data.reason.strip(), data.excluded_segment_ids),
        )

    async def segment_history(
        self, actor: Actor, revision_id: UUID
    ) -> list[SegmentReviewEventData]:
        require_role(actor, Role.ADMIN)
        return await self.gateway.segment_history(revision_id)

    async def admin_list(
        self, actor: Actor, filters: AdminInventoryFilters | None = None
    ) -> list[AdminSourceData]:
        require_role(actor, Role.ADMIN)
        return await self.gateway.admin_list(filters or AdminInventoryFilters())

    async def approve(
        self, actor: Actor, revision_id: UUID, data: ApprovalData
    ) -> AdminRevisionData:
        require_role(actor, Role.ADMIN)
        if not data.user_text or not data.sensitivity_cleared:
            raise SourceInputError("User text rights and sensitivity clearance required")
        evidence = urlsplit(data.evidence_url)
        local_attestation = (
            self.local_test_mode
            and evidence.scheme == "local-test"
            and evidence.hostname == "user-attestation"
            and bool(evidence.path.strip("/"))
            and not data.provider_transfer
        )
        if not local_attestation and (evidence.scheme != "https" or not evidence.hostname):
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
