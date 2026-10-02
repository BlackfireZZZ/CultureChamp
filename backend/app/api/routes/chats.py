"""Transport contracts for owned, persisted text chats."""

from datetime import datetime
from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.auth import current_user
from app.application.access import Actor
from app.application.chat import ChatCitationData, ChatData, ChatService, ChatTurnData
from app.application.generation import GenerationService, GenerationUnavailable
from app.application.retrieval import RetrievalService
from app.core.config import settings
from app.infrastructure.db.chat_store import SqlChatStore
from app.infrastructure.db.citation_resolver import SqlCitationResolver
from app.infrastructure.db.model_quota import SqlModelQuota
from app.infrastructure.db.session import session_factory
from app.infrastructure.db.vector_search import SqlGovernedVectorSearch
from app.infrastructure.model.application_adapter import GatewayModelPort
from app.infrastructure.model.gateway import ModelGateway, ModelProvider
from app.infrastructure.vector.text_vectors import LocalTextEmbedder, QdrantTextIndex

router = APIRouter(prefix="/chats", tags=["chats"])


def get_chat_service(request: Request) -> ChatService:
    factory: async_sessionmaker[AsyncSession] = getattr(
        request.app.state, "source_session_factory", session_factory
    )
    provider: ModelProvider | None = getattr(request.app.state, "model_provider", None)
    if provider is None:
        raise GenerationUnavailable("Model provider unavailable")
    index: QdrantTextIndex = getattr(
        request.app.state,
        "vector_index",
        QdrantTextIndex(settings.vector_url, LocalTextEmbedder()),
    )
    generation = GenerationService(
        RetrievalService(
            SqlGovernedVectorSearch(factory, index)
        ),
        GatewayModelPort(ModelGateway(provider, SqlModelQuota(factory))),
        SqlCitationResolver(factory),
        external=bool(getattr(provider, "requires_provider_transfer", False)),
    )
    return ChatService(SqlChatStore(factory), generation)


class ChatSummaryView(BaseModel):
    id: UUID
    title: str
    updated_at: datetime


class ChatCitationView(BaseModel):
    revision_id: UUID
    segment_id: UUID
    page: int | None
    section: str | None
    sheet: str | None
    table: str | None
    row_start: int | None
    row_end: int | None
    column_start: int | None
    column_end: int | None
    available: bool


class ChatTurnView(BaseModel):
    request_id: UUID
    ordinal: int
    user_text: str
    assistant_text: str | None
    evidence_status: str | None
    status: str
    citations: list[ChatCitationView]
    rating: Literal["up", "down"] | None
    feedback_comment: str | None


class ChatDetailView(ChatSummaryView):
    turns: list[ChatTurnView]


class SendInput(BaseModel):
    request_id: UUID
    text: str = Field(min_length=1, max_length=2_000)
    starter_id: Literal["UC-01", "UC-02", "UC-03", "UC-04", "UC-05", "UC-06"] | None = None


class FeedbackInput(BaseModel):
    rating: Literal["up", "down"] | None
    comment: str | None = Field(default=None, max_length=1_000)


def _summary(data: ChatData) -> ChatSummaryView:
    return ChatSummaryView(id=data.id, title=data.title, updated_at=data.updated_at)


def _citation(data: ChatCitationData) -> ChatCitationView:
    locator = data.locator
    return ChatCitationView(
        revision_id=data.revision_id,
        segment_id=data.segment_id,
        page=locator.page,
        section=locator.section,
        sheet=locator.sheet,
        table=locator.table,
        row_start=locator.row_start,
        row_end=locator.row_end,
        column_start=locator.column_start,
        column_end=locator.column_end,
        available=data.available,
    )


def _turn(data: ChatTurnData) -> ChatTurnView:
    return ChatTurnView(
        request_id=data.request_id,
        ordinal=data.ordinal,
        user_text=data.user_text,
        assistant_text=data.assistant_text,
        evidence_status=data.evidence_status,
        status=data.status,
        citations=[_citation(item) for item in data.citations],
        rating=cast(Literal["up", "down"] | None, data.rating),
        feedback_comment=data.feedback_comment,
    )


@router.post("", response_model=ChatSummaryView, status_code=201)
async def create_chat(
    response: Response,
    actor: Annotated[Actor, Depends(current_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatSummaryView:
    response.headers["Cache-Control"] = "no-store"
    return _summary(await service.create(actor))


@router.get("", response_model=list[ChatSummaryView])
async def list_chats(
    response: Response,
    actor: Annotated[Actor, Depends(current_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> list[ChatSummaryView]:
    response.headers["Cache-Control"] = "no-store"
    return [_summary(item) for item in await service.list(actor)]


@router.get("/{chat_id}", response_model=ChatDetailView)
async def chat_detail(
    chat_id: UUID,
    response: Response,
    actor: Annotated[Actor, Depends(current_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatDetailView:
    response.headers["Cache-Control"] = "no-store"
    data = await service.detail(actor, chat_id)
    return ChatDetailView(**_summary(data).model_dump(), turns=[_turn(item) for item in data.turns])


@router.delete("/{chat_id}", status_code=204)
async def delete_chat(
    chat_id: UUID,
    actor: Annotated[Actor, Depends(current_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> None:
    await service.delete(actor, chat_id)


@router.post("/{chat_id}/messages", response_model=ChatTurnView)
async def send_message(
    chat_id: UUID,
    data: SendInput,
    response: Response,
    actor: Annotated[Actor, Depends(current_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatTurnView:
    if not data.text.strip():
        raise HTTPException(status_code=422, detail="Chat message must contain text")
    response.headers["Cache-Control"] = "no-store"
    return _turn(await service.send(actor, chat_id, data.request_id, data.text, data.starter_id))


@router.put("/{chat_id}/messages/{request_id}/feedback", response_model=ChatTurnView)
async def rate_message(
    chat_id: UUID,
    request_id: UUID,
    data: FeedbackInput,
    response: Response,
    actor: Annotated[Actor, Depends(current_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatTurnView:
    if data.rating is None and data.comment is not None:
        raise HTTPException(status_code=422, detail="Comment requires a rating")
    response.headers["Cache-Control"] = "no-store"
    return _turn(await service.rate(actor, chat_id, request_id, data.rating, data.comment))
