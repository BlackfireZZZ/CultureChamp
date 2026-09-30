"""Source identity, exact locators and fail-closed publication rules."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class SegmentKind(StrEnum):
    PROSE = "prose"
    TABLE = "table"


class DecisionKind(StrEnum):
    APPROVE = "approve"
    REVOKE = "revoke"


@dataclass(frozen=True, slots=True)
class Locator:
    page: int | None = None
    section: str | None = None
    sheet: str | None = None
    table: str | None = None
    row_start: int | None = None
    row_end: int | None = None
    column_start: int | None = None
    column_end: int | None = None

    def __post_init__(self) -> None:
        if self.page is not None and self.page < 1:
            raise ValueError("page must be one-based")
        if self.section is not None and not self.section.strip():
            raise ValueError("section cannot be blank")
        for start, end in (
            (self.row_start, self.row_end),
            (self.column_start, self.column_end),
        ):
            if (start is None) != (end is None):
                raise ValueError("locator range needs both endpoints")
            if start is not None and (start < 1 or end is None or end < start):
                raise ValueError("locator range must be positive and ordered")
        has_table_range = self.row_start is not None or self.column_start is not None
        if has_table_range and (self.row_start is None or self.column_start is None):
            raise ValueError("table locator needs row and column ranges")
        if has_table_range and not (self.sheet or self.table):
            raise ValueError("table locator needs sheet or table")
        if self.page is None and self.section is None and not has_table_range:
            raise ValueError("locator needs a page, section or table range")


@dataclass(frozen=True, slots=True)
class Citation:
    revision_id: UUID
    segment_id: UUID
    locator: Locator


@dataclass(frozen=True, slots=True)
class RightsScopes:
    user_text: bool = False
    original_file: bool = False
    provider_transfer: bool = False


@dataclass(frozen=True, slots=True)
class RevisionDecision:
    revision_id: UUID
    kind: DecisionKind
    rights: RightsScopes
    sensitivity_cleared: bool

    def allows_user_text(self) -> bool:
        return (
            self.kind is DecisionKind.APPROVE and self.rights.user_text and self.sensitivity_cleared
        )

    def allows_provider_transfer(self) -> bool:
        return self.allows_user_text() and self.rights.provider_transfer

    def allows_original(self) -> bool:
        return self.allows_user_text() and self.rights.original_file
