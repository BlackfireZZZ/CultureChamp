import asyncio

import httpx
import pytest

from app.infrastructure.model.gateway import (
    FakeModelProvider,
    ModelFailure,
    ModelGateway,
    ModelRequest,
    ModelResult,
    TemporaryModelFailure,
)
from app.infrastructure.model.http import HttpModelProvider


class AllowQuota:
    async def reserve(self, subject_id: str, idempotency_key: str) -> bool:
        return True

    async def finish(
        self, subject_id: str, idempotency_key: str, result: ModelResult | None
    ) -> None:
        pass


class DenyQuota:
    async def reserve(self, subject_id: str, idempotency_key: str) -> bool:
        return False

    async def finish(
        self, subject_id: str, idempotency_key: str, result: ModelResult | None
    ) -> None:
        pass


class SlowProvider:
    async def generate(self, request: ModelRequest) -> ModelResult:
        await asyncio.sleep(1)
        return ModelResult("late", 1, 1)


class RetryProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, request: ModelRequest) -> ModelResult:
        self.calls += 1
        if self.calls == 1:
            raise TemporaryModelFailure("provider_unavailable")
        return ModelResult("safe", 1, 1)


def request() -> ModelRequest:
    return ModelRequest("user-1", "Write a brief", "turn-1")


def test_fake_quota_retry_and_timeout() -> None:
    asyncio.run(_fake_quota_retry_and_timeout())


async def _fake_quota_retry_and_timeout() -> None:
    fake = ModelGateway(FakeModelProvider(), AllowQuota())
    assert "Demo response only" in (await fake.generate(request())).text
    with pytest.raises(ModelFailure, match="quota_exceeded"):
        await ModelGateway(FakeModelProvider(), DenyQuota()).generate(request())
    retry = RetryProvider()
    assert (await ModelGateway(retry, AllowQuota()).generate(request())).text == "safe"
    assert retry.calls == 2
    with pytest.raises(ModelFailure, match="timeout"):
        await ModelGateway(SlowProvider(), AllowQuota(), deadline_seconds=0.01).generate(request())


def test_http_provider_disabled_and_safe_errors(caplog: pytest.LogCaptureFixture) -> None:
    asyncio.run(_http_provider_disabled_and_safe_errors(caplog))


async def _http_provider_disabled_and_safe_errors(caplog: pytest.LogCaptureFixture) -> None:
    secret = "super-secret-canary"
    prompt = "private-prompt-canary"
    calls: list[httpx.Request] = []

    def handler(outgoing: httpx.Request) -> httpx.Response:
        calls.append(outgoing)
        return httpx.Response(503, text=f"{secret} {prompt}")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = HttpModelProvider(
            endpoint="https://approved.example/v1/chat/completions",
            model="pilot-model",
            api_key=secret,
            client=client,
        )
        with pytest.raises(ModelFailure, match="provider_disabled"):
            await provider.generate(ModelRequest("user-1", prompt, "turn-1"))
        assert calls == []
        provider.policy_approved = True
        with pytest.raises(ModelFailure, match="provider_disabled"):
            await provider.generate(ModelRequest("user-1", prompt, "turn-1"))
        assert calls == []
        with pytest.raises(ModelFailure, match="provider_unavailable") as failure:
            await ModelGateway(provider, AllowQuota()).generate(
                ModelRequest("user-1", prompt, "turn-1", provider_transfer_permitted=True)
            )
        assert len(calls) == 2
        assert secret not in str(failure.value)
        assert prompt not in str(failure.value)
        assert secret not in caplog.text
        assert prompt not in caplog.text


def test_http_provider_parses_bounded_response() -> None:
    asyncio.run(_http_provider_parses_bounded_response())


async def _http_provider_parses_bounded_response() -> None:
    def handler(outgoing: httpx.Request) -> httpx.Response:
        assert outgoing.headers["idempotency-key"] == "turn-1"
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "A proposal"}}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = HttpModelProvider(
            endpoint="https://approved.example/v1/chat/completions",
            model="pilot-model",
            api_key="test-key",
            policy_approved=True,
            client=client,
        )
        result = await ModelGateway(provider, AllowQuota()).generate(
            ModelRequest("user-1", "Write a brief", "turn-1", provider_transfer_permitted=True)
        )
        assert result == ModelResult("A proposal", 3, 2)


def test_http_provider_rejects_oversized_response() -> None:
    async def check() -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"x" * 1_000_001)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = HttpModelProvider(
                endpoint="https://approved.example/v1/chat/completions",
                model="pilot-model",
                api_key="test-key",
                policy_approved=True,
                client=client,
            )
            with pytest.raises(ModelFailure, match="provider_unavailable"):
                await provider.generate(
                    ModelRequest("user-1", "brief", "turn-1", provider_transfer_permitted=True)
                )

    asyncio.run(check())
