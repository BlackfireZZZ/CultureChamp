from uuid import uuid4

import pytest

from app.domain.sources import Citation, DecisionKind, Locator, RevisionDecision, RightsScopes


def test_citation_preserves_exact_revision_and_physical_page() -> None:
    revision_id, segment_id = uuid4(), uuid4()
    citation = Citation(revision_id, segment_id, Locator(page=3, section="Introduction"))
    assert citation.revision_id == revision_id
    assert citation.segment_id == segment_id
    assert citation.locator.page == 3


@pytest.mark.parametrize(
    "locator",
    [
        Locator(page=1),
        Locator(sheet="Data", row_start=2, row_end=4, column_start=1, column_end=3),
    ],
)
def test_locator_accepts_exact_page_or_table_range(locator: Locator) -> None:
    assert locator.page is not None or locator.row_start is not None


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"page": 0},
        {"sheet": "Data", "row_start": 3, "row_end": 2, "column_start": 1, "column_end": 1},
        {"row_start": 1, "row_end": 1, "column_start": 1, "column_end": 1},
    ],
)
def test_locator_rejects_ambiguous_or_invalid_location(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        Locator(**kwargs)  # type: ignore[arg-type]


def test_approval_requires_rights_and_sensitivity_and_revocation_fails_closed() -> None:
    revision_id = uuid4()
    rights = RightsScopes(user_text=True, original_file=False, provider_transfer=False)
    approval = RevisionDecision(revision_id, DecisionKind.APPROVE, rights, True)
    assert approval.allows_user_text()
    assert not approval.allows_original()
    assert not approval.allows_provider_transfer()
    assert not RevisionDecision(revision_id, DecisionKind.APPROVE, rights, False).allows_user_text()
    assert not RevisionDecision(revision_id, DecisionKind.REVOKE, rights, True).allows_user_text()
    no_rights = RevisionDecision(revision_id, DecisionKind.APPROVE, RightsScopes(), True)
    assert not no_rights.allows_user_text()
