import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.application.access import Actor, Role
from app.application.source_management import ApprovalData, SourceInputError, SourceService


def test_local_attestation_is_explicitly_enabled_and_never_allows_provider_transfer() -> None:
    gateway = AsyncMock()
    actor = Actor("local-admin", Role.ADMIN)
    revision_id = uuid4()
    approval = ApprovalData(
        reason="User-authorized local testing only; reuse rights unverified",
        evidence_url="local-test://user-attestation/2026-10-02",
        user_text=True,
        original_file=True,
        provider_transfer=False,
        sensitivity_cleared=True,
    )

    async def check() -> None:
        with pytest.raises(SourceInputError):
            await SourceService(gateway).approve(actor, revision_id, approval)
        gateway.approve.assert_not_awaited()

        await SourceService(gateway, local_test_mode=True).approve(actor, revision_id, approval)
        gateway.approve.assert_awaited_once_with(revision_id, actor.subject_id, approval)

        with pytest.raises(SourceInputError):
            await SourceService(gateway, local_test_mode=True).approve(
                actor, revision_id,
                ApprovalData(**{**approval.__dict__, "provider_transfer": True}),
            )

    asyncio.run(check())
