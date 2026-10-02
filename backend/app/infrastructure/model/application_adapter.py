"""Adapt application generation calls to the bounded model gateway."""

from collections.abc import Awaitable, Callable

from app.application.generation import GenerationRateLimited, GenerationUnavailable, ModelCall
from app.infrastructure.model.gateway import ModelFailure, ModelGateway, ModelRequest


class GatewayModelPort:
    def __init__(self, gateway: ModelGateway) -> None:
        self.gateway = gateway

    async def generate(self, call: ModelCall) -> str:
        try:
            result = await self.gateway.generate(
                ModelRequest(
                    subject_id=call.subject_id,
                    prompt=call.prompt,
                    idempotency_key=call.request_id,
                    provider_transfer_permitted=call.external,
                    system_prompt=call.system,
                )
            )
            return result.text
        except ModelFailure as exc:
            if exc.code == "quota_exceeded":
                raise GenerationRateLimited("Model quota exceeded") from exc
            raise GenerationUnavailable("Model provider unavailable or rate limited") from exc

    async def generate_stream(
        self, call: ModelCall, on_delta: Callable[[str], Awaitable[None]]
    ) -> str:
        try:
            result = await self.gateway.generate_stream(
                ModelRequest(
                    subject_id=call.subject_id,
                    prompt=call.prompt,
                    idempotency_key=call.request_id,
                    provider_transfer_permitted=call.external,
                    system_prompt=call.system,
                ),
                on_delta,
            )
            return result.text
        except ModelFailure as exc:
            if exc.code == "quota_exceeded":
                raise GenerationRateLimited("Model quota exceeded") from exc
            raise GenerationUnavailable("Model provider unavailable or rate limited") from exc
