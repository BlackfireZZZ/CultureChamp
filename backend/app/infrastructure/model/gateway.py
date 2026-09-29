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


class FakeModelProvider:
    """Deterministic test provider. It does not infer or claim cultural facts."""

    async def generate(self, request: ModelRequest) -> ModelResult:
        return ModelResult(
            text="Demo response only. No cultural claim or source citation is verified.",
            input_tokens=len(request.prompt.split()),
            output_tokens=12,
        )


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
        if request.max_output_tokens < 1 or request.max_output_tokens > 2_000:
            raise ModelFailure("invalid_input")
        if not await self.quota.reserve(request.subject_id, request.idempotency_key):
            raise ModelFailure("quota_exceeded")

        async def run() -> ModelResult:
            try:
                return await self.provider.generate(request)
            except TemporaryModelFailure:
                return await self.provider.generate(request)

        try:
            return await asyncio.wait_for(run(), timeout=self.deadline_seconds)
        except TimeoutError as exc:
            raise ModelFailure("timeout") from exc
        except ModelFailure:
            raise
        except Exception as exc:
            raise ModelFailure("provider_unavailable") from exc
