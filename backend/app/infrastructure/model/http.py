import json
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
            text = payload["choices"][0]["message"]["content"]
            usage = payload["usage"]
            if not isinstance(text, str) or not text:
                raise ValueError("empty model result")
            return ModelResult(
                text=text,
                input_tokens=int(usage["prompt_tokens"]),
                output_tokens=int(usage["completion_tokens"]),
            )
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise TemporaryModelFailure("provider_unavailable") from exc
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ModelFailure("provider_unavailable") from exc
        finally:
            if owned_client:
                await client.aclose()
