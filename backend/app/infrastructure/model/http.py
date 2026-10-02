import json
from collections.abc import Awaitable, Callable
from urllib.parse import urlparse

import httpx

from app.infrastructure.model.gateway import (
    ModelFailure,
    ModelRequest,
    ModelResult,
    TemporaryModelFailure,
)


class HttpModelProvider:
    """OpenAI-compatible wire adapter, disabled until an external data policy is approved."""

    requires_provider_transfer = True

    def __init__(
        self,
        *,
        endpoint: str,
        model: str,
        api_key: str,
        policy_approved: bool = False,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        parsed = urlparse(endpoint)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("endpoint must be an HTTPS URL without embedded credentials")
        self.endpoint = endpoint
        self.model = model
        self.api_key = api_key
        self.policy_approved = policy_approved
        self.client = client

    async def generate(self, request: ModelRequest) -> ModelResult:
        if not self.policy_approved:
            raise ModelFailure("provider_disabled")
        if not request.provider_transfer_permitted:
            raise ModelFailure("provider_disabled")
        if not self.api_key:
            raise ModelFailure("provider_unavailable")
        owned_client = self.client is None
        client = self.client or httpx.AsyncClient(
            timeout=httpx.Timeout(25.0, connect=5.0, pool=2.0),
            follow_redirects=False,
            trust_env=False,
        )
        try:
            async with client.stream(
                "POST",
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Idempotency-Key": request.idempotency_key,
                },
                json={
                    "model": self.model,
                    "messages": [
                        *(
                            [{"role": "system", "content": request.system_prompt}]
                            if request.system_prompt
                            else []
                        ),
                        {"role": "user", "content": request.prompt},
                    ],
                    "max_tokens": request.max_output_tokens,
                    "response_format": {"type": "json_object"},
                },
            ) as response:
                if response.status_code in {429, 503}:
                    raise TemporaryModelFailure("provider_unavailable")
                if response.status_code != 200:
                    raise ModelFailure("provider_unavailable")
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > 1_000_000:
                        raise ModelFailure("provider_unavailable")
            payload = json.loads(body)
            choice = payload["choices"][0]
            if choice["finish_reason"] != "stop":
                raise ValueError("completion did not finish normally")
            text = choice["message"]["content"]
            usage = payload["usage"]
            if not isinstance(text, str) or not text:
                raise ValueError("empty model result")
            input_tokens = usage["prompt_tokens"]
            output_tokens = usage["completion_tokens"]
            if (
                type(input_tokens) is not int
                or type(output_tokens) is not int
                or input_tokens < 1
                or output_tokens < 1
            ):
                raise ValueError("invalid reported usage")
            return ModelResult(
                text=text,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise TemporaryModelFailure("provider_unavailable") from exc
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ModelFailure("provider_unavailable") from exc
        finally:
            if owned_client:
                await client.aclose()

    async def generate_stream(
        self, request: ModelRequest, on_delta: Callable[[str], Awaitable[None]]
    ) -> ModelResult:
        if not self.policy_approved or not request.provider_transfer_permitted:
            raise ModelFailure("provider_disabled")
        if not self.api_key:
            raise ModelFailure("provider_unavailable")
        owned_client = self.client is None
        client = self.client or httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=5.0, pool=2.0),
            follow_redirects=False, trust_env=False,
        )
        try:
            async with client.stream(
                "POST", self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Idempotency-Key": request.idempotency_key,
                },
                json={
                    "model": self.model,
                    "messages": [
                        *(
                            [{"role": "system", "content": request.system_prompt}]
                            if request.system_prompt else []
                        ),
                        {"role": "user", "content": request.prompt},
                    ],
                    "max_tokens": request.max_output_tokens,
                    "response_format": {"type": "json_object"},
                    "stream": True,
                    "stream_options": {"include_usage": True},
                },
            ) as response:
                if response.status_code != 200:
                    raise ModelFailure("provider_unavailable")
                pieces: list[str] = []
                received_bytes = 0
                finished = False
                done = False
                usage: object = None
                async for line in response.aiter_lines():
                    received_bytes += len(line.encode("utf-8"))
                    if received_bytes > 1_000_000:
                        raise ModelFailure("provider_unavailable")
                    if not line.startswith("data:"):
                        continue
                    data = line.removeprefix("data:").strip()
                    if data == "[DONE]":
                        done = True
                        break
                    event = json.loads(data)
                    if not isinstance(event, dict):
                        raise ValueError("invalid stream event")
                    if event.get("usage") is not None:
                        usage = event["usage"]
                    choices = event.get("choices")
                    if not isinstance(choices, list):
                        raise ValueError("invalid stream choices")
                    if not choices:
                        continue
                    choice = choices[0]
                    if not isinstance(choice, dict):
                        raise ValueError("invalid stream choice")
                    reason = choice.get("finish_reason")
                    if reason is not None:
                        if reason != "stop":
                            raise ValueError("completion did not finish normally")
                        finished = True
                    delta = choice.get("delta")
                    if not isinstance(delta, dict):
                        raise ValueError("invalid stream delta")
                    piece = delta.get("content")
                    if piece is not None:
                        if not isinstance(piece, str):
                            raise ValueError("invalid stream content")
                        pieces.append(piece)
                        await on_delta(piece)
            if not done or not finished or not pieces or not isinstance(usage, dict):
                raise ModelFailure("provider_unavailable")
            input_tokens = usage.get("prompt_tokens")
            output_tokens = usage.get("completion_tokens")
            if (
                type(input_tokens) is not int or type(output_tokens) is not int
                or input_tokens < 1 or output_tokens < 1
            ):
                raise ModelFailure("provider_unavailable")
            return ModelResult("".join(pieces), input_tokens, output_tokens)
        except (httpx.TimeoutException, httpx.RequestError, KeyError, IndexError,
                TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ModelFailure("provider_unavailable") from exc
        finally:
            if owned_client:
                await client.aclose()
