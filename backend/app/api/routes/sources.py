"""Transport contracts for governed candidate and visible materials."""

from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.auth import current_admin, current_user
from app.application.access import Actor
from app.application.source_management import (
    AdminRevisionData,
    ApprovalData,
    MaterialData,
    SourceService,
)
from app.core.config import settings
from app.infrastructure.db.governed_sources import SqlSourceGateway
from app.infrastructure.db.session import session_factory
from app.infrastructure.ingestion.storage import PrivatePdfStore

admin_router = APIRouter(prefix="/admin", tags=["admin-sources"])
materials_router = APIRouter(prefix="/materials", tags=["materials"])


def get_source_service(request: Request) -> SourceService:
    factory: async_sessionmaker[AsyncSession] = getattr(
        request.app.state, "source_session_factory", session_factory
    )
    store: PrivatePdfStore = getattr(request.app.state, "source_store", None) or PrivatePdfStore(
        Path(settings.source_storage_root)
    )
    return SourceService(SqlSourceGateway(factory, store))


class IntakeView(BaseModel):
    source_id: UUID
    revision_id: UUID
    status: str


class LocatorView(BaseModel):
    kind: str = "page"
    page: int


class SegmentView(BaseModel):
    segment_id: UUID
    locator: LocatorView
    text: str


class MaterialView(BaseModel):
    revision_id: UUID
    title: str
    creator: str | None
    origin_url: str
    rights_usage_note: str | None
    region: str | None = None
    people: str | None = None
    period: str | None = None
    media_type: str


class MaterialDetail(MaterialView):
    segments: list[SegmentView]


class TagView(BaseModel):
    kind: str
    value: str


class AdminRevisionView(MaterialDetail):
    source_id: UUID
    status: str
    error_code: str | None
    decision: str | None
    sha256: str
    tags: list[TagView]


class AdminSourceView(BaseModel):
    source_id: UUID
    revision_id: UUID
    title: str
    origin_url: str
    status: str
    decision: str | None


class DecisionInput(BaseModel):
    reason: str = Field(min_length=10, max_length=2000)
    evidence_url: str = Field(min_length=8, max_length=2000)
    user_text: bool = False
    original_file: bool = False
    provider_transfer: bool = False
    sensitivity_cleared: bool = False


class RevokeInput(BaseModel):
    reason: str = Field(min_length=10, max_length=2000)


def _material_view(material: MaterialData) -> MaterialView:
    return MaterialView(
        revision_id=material.revision_id,
        title=material.title,
        creator=material.creator,
        origin_url=material.origin_url,
        rights_usage_note=material.rights_usage_note,
        media_type=material.media_type,
    )


def _detail_view(material: MaterialData) -> MaterialDetail:
    view = _material_view(material)
    return MaterialDetail(
        **view.model_dump(),
        segments=[
            SegmentView(segment_id=s.segment_id, locator=LocatorView(page=s.page), text=s.text)
            for s in material.segments
        ],
    )


def _admin_view(data: AdminRevisionData) -> AdminRevisionView:
    detail = _detail_view(data.material)
    return AdminRevisionView(
        **detail.model_dump(),
        source_id=data.source_id,
        status=data.status,
        error_code=data.error_code,
        decision=data.decision,
        sha256=data.sha256,
        tags=[TagView(kind=tag.kind, value=tag.value) for tag in data.tags],
    )


@admin_router.post("/sources", response_model=IntakeView, status_code=201)
async def upload_source(
    actor: Annotated[Actor, Depends(current_admin)],
    service: Annotated[SourceService, Depends(get_source_service)],
    file: Annotated[UploadFile, File()],
    origin_url: Annotated[str, Form(min_length=8, max_length=2000)],
    title: Annotated[str, Form(min_length=1, max_length=500)],
    creator: Annotated[str | None, Form()] = None,
    rights_note: Annotated[str | None, Form(max_length=2000)] = None,
    source_id: Annotated[UUID | None, Form()] = None,
    tags: Annotated[list[str] | None, Form()] = None,
) -> IntakeView:
    result = await service.upload(
        actor,
        origin_url=origin_url,
        title=title,
        creator=creator,
        rights_note=rights_note,
        source_id=source_id,
        stream=file.file,
        filename=file.filename or "",
        media_type=file.content_type or "",
        tags=tags,
    )
    return IntakeView(
        source_id=result.source_id, revision_id=result.revision_id, status=result.status
    )


@admin_router.get("/revisions/{revision_id}", response_model=AdminRevisionView)
async def admin_revision(
    revision_id: UUID,
    actor: Annotated[Actor, Depends(current_admin)],
    service: Annotated[SourceService, Depends(get_source_service)],
) -> AdminRevisionView:
    return _admin_view(await service.admin_detail(actor, revision_id))


@admin_router.get("/sources", response_model=list[AdminSourceView])
async def admin_sources(
    actor: Annotated[Actor, Depends(current_admin)],
    service: Annotated[SourceService, Depends(get_source_service)],
) -> list[AdminSourceView]:
    return [AdminSourceView(**item.__dict__) for item in await service.admin_list(actor)]


@admin_router.post("/revisions/{revision_id}/approve", response_model=AdminRevisionView)
async def approve_revision(
    revision_id: UUID,
    data: DecisionInput,
    actor: Annotated[Actor, Depends(current_admin)],
    service: Annotated[SourceService, Depends(get_source_service)],
) -> AdminRevisionView:
    result = await service.approve(actor, revision_id, ApprovalData(**data.model_dump()))
    return _admin_view(result)


@admin_router.post("/revisions/{revision_id}/revoke", response_model=AdminRevisionView)
async def revoke_revision(
    revision_id: UUID,
    data: RevokeInput,
    actor: Annotated[Actor, Depends(current_admin)],
    service: Annotated[SourceService, Depends(get_source_service)],
) -> AdminRevisionView:
    return _admin_view(await service.revoke(actor, revision_id, data.reason))


@admin_router.post("/revisions/{revision_id}/retry", response_model=AdminRevisionView)
async def retry_revision(
    revision_id: UUID,
    actor: Annotated[Actor, Depends(current_admin)],
    service: Annotated[SourceService, Depends(get_source_service)],
) -> AdminRevisionView:
    return _admin_view(await service.retry(actor, revision_id))


@materials_router.get("", response_model=list[MaterialView])
async def materials_list(
    actor: Annotated[Actor, Depends(current_user)],
    service: Annotated[SourceService, Depends(get_source_service)],
) -> list[MaterialView]:
    return [_material_view(item) for item in await service.visible_list(actor)]


@materials_router.get("/{revision_id}", response_model=MaterialDetail)
async def material_detail(
    revision_id: UUID,
    actor: Annotated[Actor, Depends(current_user)],
    service: Annotated[SourceService, Depends(get_source_service)],
) -> MaterialDetail:
    return _detail_view(await service.visible_detail(actor, revision_id))
