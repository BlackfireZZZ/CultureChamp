import asyncio
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ModelRequest:
    subject_id: str
    prompt: str
    idempotency_key: str
    max_output_tokens: int = 2_000
    provider_transfer_permitted: bool = False
    system_prompt: str = ""


@dataclass(frozen=True)
class ModelResult:
    text: str
    input_tokens: int
    output_tokens: int


class ModelFailure(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class TemporaryModelFailure(ModelFailure):
    pass


class ModelProvider(Protocol):
    async def generate(self, request: ModelRequest) -> ModelResult: ...


class Quota(Protocol):
    async def reserve(self, subject_id: str, idempotency_key: str) -> bool: ...

    async def finish(
        self, subject_id: str, idempotency_key: str, result: ModelResult | None
    ) -> None: ...


class FakeModelProvider:
    """Deterministic test provider. It does not infer or claim cultural facts."""

    async def generate(self, request: ModelRequest) -> ModelResult:
        return ModelResult(
            text="Demo response only. No cultural claim or source citation is verified.",
            input_tokens=len(request.prompt.split()),
            output_tokens=12,
        )


class GroundedFakeProvider:
    """Deterministic source-echoing provider for a synthetic end-to-end check."""

    async def generate(self, request: ModelRequest) -> ModelResult:
        import json

        payload = json.loads(request.prompt)
        evidence = payload["evidence"][0]
        excerpt = evidence["excerpt"].split(".", 1)[0][:300]
        output = json.dumps(
            {
                "fact": f"The approved excerpt says: {excerpt}",
                "interpretation": "This excerpt may inform the brief; review its context.",
                "creative": "Use the brief to draft a contemporary concept, labelled as new work.",
                "citations": [evidence["id"]],
            },
            ensure_ascii=False,
        )
        return ModelResult(output, len(request.prompt.split()), len(output.split()))


class ModelGateway:
    def __init__(
        self, provider: ModelProvider, quota: Quota, *, deadline_seconds: float = 30
    ) -> None:
        if deadline_seconds <= 0:
            raise ValueError("deadline_seconds must be positive")
        self.provider = provider
        self.quota = quota
        self.deadline_seconds = deadline_seconds

    async def generate(self, request: ModelRequest) -> ModelResult:
        if not request.prompt.strip() or len(request.prompt) > 24_000:
            raise ModelFailure("invalid_input")
        if len(request.prompt.split()) > 8_000:
            raise ModelFailure("invalid_input")
        if request.max_output_tokens < 1 or request.max_output_tokens > 2_000:
            raise ModelFailure("invalid_input")
        if not await self.quota.reserve(request.subject_id, request.idempotency_key):
            raise ModelFailure("quota_exceeded")

        async def run() -> ModelResult:
            try:
                return await self.provider.generate(request)
            except TemporaryModelFailure:
                return await self.provider.generate(request)

        result: ModelResult | None = None
        try:
            result = await asyncio.wait_for(run(), timeout=self.deadline_seconds)
            if result.output_tokens > request.max_output_tokens:
                raise ModelFailure("provider_unavailable")
            return result
        except TimeoutError as exc:
            raise ModelFailure("timeout") from exc
        except ModelFailure:
            raise
        except Exception as exc:
            raise ModelFailure("provider_unavailable") from exc
        finally:
            await self.quota.finish(request.subject_id, request.idempotency_key, result)
