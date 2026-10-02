import asyncio
import json
import sys

import pytest

from app.application.generation import GenerationUnavailable
from app.infrastructure.model.gateway import GroundedFakeProvider, ModelRequest, ModelResult
from app.infrastructure.model.preflight import SEGMENT_ID, SYNTHETIC_TEXT, main, run_preflight


class RecordingSyntheticProvider(GroundedFakeProvider):
    def __init__(self) -> None:
        self.request: ModelRequest | None = None

    async def generate(self, request: ModelRequest) -> ModelResult:
        self.request = request
        return await super().generate(request)


def test_preflight_sends_only_fixed_synthetic_evidence_and_validates_citation() -> None:
    async def check() -> None:
        provider = RecordingSyntheticProvider()
        metrics = await run_preflight(provider)
        assert metrics.input_tokens > 0
        assert metrics.output_tokens > 0
        assert metrics.duration_ms >= 0
        assert provider.request is not None
        assert provider.request.provider_transfer_permitted is True
        payload = json.loads(provider.request.prompt)
        assert payload["evidence"] == [{
            "id": str(SEGMENT_ID),
            "title": "Self-authored synthetic preflight fixture",
            "creator": "Лад technical test",
            "revision_id": "ed2236df-2b22-4aa4-985f-18ed26e899ef",
            "locator": {
                "page": None, "section": "Synthetic section 1", "sheet": None,
                "table": None, "row_start": None, "row_end": None,
                "column_start": None, "column_end": None,
            },
            "context": [{"kind": "region", "value": "Invented test region"}],
            "excerpt": SYNTHETIC_TEXT,
        }]

    asyncio.run(check())


def test_preflight_rejects_provider_claim_outside_synthetic_evidence() -> None:
    class BadProvider:
        async def generate(self, request: ModelRequest) -> ModelResult:
            payload = json.loads(request.prompt)
            return ModelResult(json.dumps({
                "fact": "The synthetic swatch is red.",
                "interpretation": "A test interpretation.",
                "creative": "A new test proposal.",
                "citations": [payload["evidence"][0]["id"]],
            }), 25, 18)

    with pytest.raises(GenerationUnavailable):
        asyncio.run(run_preflight(BadProvider()))


def test_preflight_cli_requires_explicit_send_and_external_provider(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["model-preflight"])
    assert main() == 2
    assert "Pass --send-synthetic" in capsys.readouterr().err
    monkeypatch.setenv("MODEL_PROVIDER", "fake")
    monkeypatch.setattr(sys, "argv", ["model-preflight", "--send-synthetic"])
    assert main() == 1
    assert "failed" in capsys.readouterr().err
