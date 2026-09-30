import asyncio

import httpx
import pytest

from app.core.config import Settings
from app.infrastructure.model.configuration import configured_provider
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


class RecordingQuota(AllowQuota):
    def __init__(self) -> None:
        self.finished: list[ModelResult | None] = []

    async def finish(
        self, subject_id: str, idempotency_key: str, result: ModelResult | None
    ) -> None:
        self.finished.append(result)


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


def test_external_provider_configuration_fails_closed_and_keeps_key_private() -> None:
    disabled = Settings(_env_file=None, model_provider="openai_compatible",
                        model_api_endpoint="https://approved.example/v1/chat/completions",
                        model_api_name="pilot-model", model_api_key="secret-canary")
    with pytest.raises(ValueError, match="policy"):
        configured_provider(disabled)
    ready = Settings(_env_file=None, model_provider="openai_compatible",
                     model_api_endpoint="https://approved.example/v1/chat/completions",
                     model_api_name="pilot-model", model_api_key="secret-canary",
                     model_policy_approved=True)
    provider = configured_provider(ready)
    assert isinstance(provider, HttpModelProvider)
    assert provider.requires_provider_transfer is True
    assert "secret-canary" not in repr(ready)
    assert "secret-canary" not in repr(provider)


def test_fake_quota_retry_and_timeout() -> None:
    asyncio.run(_fake_quota_retry_and_timeout())


def test_over_limit_response_finishes_reservation_as_failed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def check() -> None:
        class OverLimitProvider:
            async def generate(self, request: ModelRequest) -> ModelResult:
                return ModelResult("too long", 3, 4)

        quota = RecordingQuota()
        with caplog.at_level("INFO", logger="uvicorn.error"):
            with pytest.raises(ModelFailure, match="provider_unavailable"):
                await ModelGateway(OverLimitProvider(), quota).generate(
                    ModelRequest("user-1", "Write a brief", "turn-1", max_output_tokens=3)
                )
        assert quota.finished == [None]

    asyncio.run(check())
    assert "model_call outcome=provider_unavailable" in caplog.text
    assert "input_tokens=3 output_tokens=4" in caplog.text


def test_gateway_logs_duration_and_usage_without_request_content(
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def check() -> None:
        class MeteredProvider:
            async def generate(self, request: ModelRequest) -> ModelResult:
                return ModelResult("private-response-canary", 7, 3)

        with caplog.at_level("INFO", logger="uvicorn.error"):
            await ModelGateway(MeteredProvider(), AllowQuota()).generate(
                ModelRequest("private-user-canary", "private-prompt-canary", "private-key-canary")
            )

    asyncio.run(check())
    assert "model_call outcome=ok" in caplog.text
    assert "duration_ms=" in caplog.text
    assert "input_tokens=7 output_tokens=3" in caplog.text
    for canary in (
        "private-response-canary",
        "private-user-canary",
        "private-prompt-canary",
        "private-key-canary",
    ):
        assert canary not in caplog.text


def test_gateway_does_not_log_unrecognized_provider_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def check() -> None:
        class BadProvider:
            async def generate(self, request: ModelRequest) -> ModelResult:
                raise ModelFailure("private-error-canary")

        with caplog.at_level("INFO", logger="uvicorn.error"):
            with pytest.raises(ModelFailure):
                await ModelGateway(BadProvider(), AllowQuota()).generate(request())

    asyncio.run(check())
    assert "model_call outcome=provider_unavailable" in caplog.text
    assert "private-error-canary" not in caplog.text


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
