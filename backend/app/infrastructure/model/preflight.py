"""Check a selected text provider with fixed, self-authored synthetic evidence."""

import argparse
import asyncio
import sys
import time
from dataclasses import dataclass
from uuid import UUID, uuid4

from app.application.access import Actor, Role
from app.application.generation import GenerationService, GenerationUnavailable
from app.application.retrieval import EvidenceSegment, RetrievalService
from app.core.config import Settings
from app.domain.sources import Citation, Locator
from app.infrastructure.model.application_adapter import GatewayModelPort
from app.infrastructure.model.configuration import configured_provider
from app.infrastructure.model.gateway import ModelGateway, ModelProvider, ModelResult

REVISION_ID = UUID("ed2236df-2b22-4aa4-985f-18ed26e899ef")
SEGMENT_ID = UUID("a5a28694-d005-4025-a6b5-b15c8283f708")
SYNTHETIC_TEXT = "The self-authored synthetic swatch is blue."
SYNTHETIC_LOCATOR = Locator(section="Synthetic section 1")


class SyntheticSearch:
    async def search(
        self,
        query: str,
        *,
        limit: int,
        region: str | None,
        people: str | None,
        for_provider: bool,
    ) -> tuple[EvidenceSegment, ...]:
        if not for_provider:
            raise GenerationUnavailable("Synthetic preflight requires provider mode")
        return (
            EvidenceSegment(
                REVISION_ID,
                SEGMENT_ID,
                "Self-authored synthetic preflight fixture",
                "Лад technical test",
                SYNTHETIC_LOCATOR,
                SYNTHETIC_TEXT,
                1.0,
                context_tags=(("region", "Invented test region"),),
            ),
        )


class SyntheticCitation:
    async def resolve(self, revision_id: UUID, segment_id: UUID) -> Citation | None:
        if revision_id == REVISION_ID and segment_id == SEGMENT_ID:
            return Citation(REVISION_ID, SEGMENT_ID, SYNTHETIC_LOCATOR)
        return None


class CaptureQuota:
    def __init__(self) -> None:
        self.result: ModelResult | None = None
        self.accepted = False

    async def reserve(self, subject_id: str, idempotency_key: str) -> bool:
        return True

    async def finish(
        self,
        subject_id: str,
        idempotency_key: str,
        result: ModelResult | None,
        *,
        accepted: bool = True,
    ) -> None:
        self.result = result
        self.accepted = accepted


@dataclass(frozen=True, slots=True)
class PreflightMetrics:
    input_tokens: int
    output_tokens: int
    duration_ms: int


async def run_preflight(provider: ModelProvider) -> PreflightMetrics:
    quota = CaptureQuota()
    service = GenerationService(
        RetrievalService(SyntheticSearch()),
        GatewayModelPort(ModelGateway(provider, quota)),
        SyntheticCitation(),
        external=True,
    )
    started = time.monotonic_ns()
    answer = await service.generate(
        Actor("synthetic-preflight", Role.USER),
        "Suggest one new color concept from the supplied synthetic fixture; "
        "cite the fact exactly and keep the invented idea separate.",
        str(uuid4()),
    )
    if (
        answer.evidence_status != "grounded"
        or answer.citations != (Citation(REVISION_ID, SEGMENT_ID, SYNTHETIC_LOCATOR),)
        or not quota.accepted
        or quota.result is None
    ):
        raise GenerationUnavailable("Synthetic provider preflight failed validation")
    return PreflightMetrics(
        quota.result.input_tokens,
        quota.result.output_tokens,
        (time.monotonic_ns() - started) // 1_000_000,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--send-synthetic", action="store_true",
        help="Send one fixed self-authored synthetic prompt to the configured provider",
    )
    args = parser.parse_args()
    if not args.send_synthetic:
        print("Pass --send-synthetic to make the provider request.", file=sys.stderr)
        return 2
    try:
        settings = Settings()
        if settings.model_provider != "openai_compatible":
            raise ValueError("external provider is not selected")
        metrics = asyncio.run(run_preflight(configured_provider(settings)))
    except Exception:
        print("Synthetic provider preflight failed; no response content was printed.",
              file=sys.stderr)
        return 1
    print(
        "Synthetic provider preflight passed: "
        f"input_tokens={metrics.input_tokens} "
        f"output_tokens={metrics.output_tokens} duration_ms={metrics.duration_ms}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
