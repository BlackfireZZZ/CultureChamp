import asyncio
import logging
from uuid import uuid4

import pytest

from app.api.routes.chat_stream import stream_message
from app.api.routes.chats import SendInput
from app.application.access import Actor, Role
from app.application.chat import ChatService, TurnClaim
from app.application.generation import GeneratedAnswer, GenerationValidationFailure


@pytest.mark.parametrize("stage", ["generation", "persistence"])
def test_stream_failure_logs_stage_without_private_exception_text(stage, caplog) -> None:
    private = "private prompt, model response, SQL parameters and credential"

    class Store:
        failed = False

        async def claim(self, *args):
            return TurnClaim(1, None)

        async def finish(self, *args):
            raise RuntimeError(private)

        async def fail(self, *args):
            self.failed = True

    class Generation:
        async def generate_stream(self, actor, text, request_id, on_delta):
            if stage == "generation":
                try:
                    raise ValueError(private)
                except ValueError as exc:
                    raise GenerationValidationFailure("invalid_json") from exc
            return GeneratedAnswer("Synthetic answer", (), "insufficient")

    async def check():
        store = Store()
        response = await stream_message(
            uuid4(), SendInput(request_id=uuid4(), text=private),
            Actor("synthetic-owner", Role.USER), ChatService(store, Generation()),
        )
        events = [chunk async for chunk in response.body_iterator]
        assert len(events) == 1
        assert "event: error" in events[0]
        assert "Generation unavailable" in events[0]
        assert private not in events[0]
        assert store.failed

    with caplog.at_level(logging.WARNING):
        asyncio.run(check())
    assert f"stage={stage}" in caplog.text
    if stage == "generation":
        assert "reason=invalid_json" in caplog.text
    assert private not in caplog.text
    assert "Traceback" not in caplog.text
