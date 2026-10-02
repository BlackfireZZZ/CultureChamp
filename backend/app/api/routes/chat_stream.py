"""Stream provisional model prose, then persist and send the validated chat turn."""

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import suppress
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.auth import current_user
from app.api.routes.chats import SendInput, _turn, get_chat_service
from app.application.access import Actor
from app.application.chat import ChatConflict, ChatNotFound, ChatService
from app.application.generation import GenerationRateLimited

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("/{chat_id}/messages/stream")
async def stream_message(
    chat_id: UUID,
    data: SendInput,
    actor: Annotated[Actor, Depends(current_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> StreamingResponse:
    if not data.text.strip():
        raise HTTPException(status_code=422, detail="Chat message must contain text")

    async def events() -> AsyncIterator[str]:
        queue: asyncio.Queue[tuple[str, dict[str, object]] | None] = asyncio.Queue()

        async def on_delta(value: str) -> None:
            await queue.put(("delta", {"text": value}))

        async def produce() -> None:
            attempt: int | None = None
            try:
                claim = await service.store.claim(
                    actor.subject_id, chat_id, data.request_id, data.text.strip(),
                    data.starter_id,
                )
                if claim.completed is not None:
                    await queue.put(("complete", {
                        "turn": _turn(claim.completed).model_dump(mode="json")
                    }))
                    return
                attempt = claim.attempt
                if attempt is None:
                    raise ChatConflict("Chat turn could not be claimed")
                answer = await service.generation.generate_stream(
                    actor, data.text.strip(), str(data.request_id), on_delta
                )
                turn = await service.store.finish(
                    actor.subject_id, chat_id, data.request_id, attempt, answer
                )
                await queue.put(("complete", {"turn": _turn(turn).model_dump(mode="json")}))
            except asyncio.CancelledError:
                if attempt is not None:
                    with suppress(Exception):
                        await service.store.fail(
                            actor.subject_id, chat_id, data.request_id, attempt
                        )
                raise
            except Exception as exc:
                if attempt is not None:
                    with suppress(Exception):
                        await service.store.fail(
                            actor.subject_id, chat_id, data.request_id, attempt
                        )
                message = (
                    "Chat unavailable" if isinstance(exc, ChatNotFound)
                    else "Chat conflict" if isinstance(exc, ChatConflict)
                    else "Generation limit reached" if isinstance(exc, GenerationRateLimited)
                    else "Generation unavailable"
                )
                await queue.put(("error", {"message": message}))
            finally:
                await queue.put(None)

        task = asyncio.create_task(produce())
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                name, payload = event
                yield f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
        finally:
            if not task.done():
                task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    return StreamingResponse(
        events(), media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
