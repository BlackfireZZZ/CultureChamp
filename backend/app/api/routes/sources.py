"""Admin candidate intake and fail-closed user material views."""

from pathlib import Path
from typing import Annotated
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.auth import current_admin, current_user
from app.application.access import Actor
from app.core.config import settings
from app.domain.sources import DecisionKind, RevisionDecision, RightsScopes
from app.infrastructure.db.session import session_factory
from app.infrastructure.db.source_models import (
    Source,
    SourceDecision,
    SourceProcessing,
    SourceRevision,
    SourceSegment,
)
from app.infrastructure.db.source_repository import SourceRepository
from app.infrastructure.ingestion.storage import IntakeError, PrivatePdfStore

admin_router = APIRouter(prefix="/admin", tags=["admin-sources"])
materials_router = APIRouter(prefix="/materials", tags=["materials"])


def _factory(request: Request) -> async_sessionmaker[AsyncSession]:
    return getattr(request.app.state, "source_session_factory", session_factory)


def _store(request: Request) -> PrivatePdfStore:
    configured = getattr(request.app.state, "source_store", None)
    return (
        configured
        if configured is not None
        else PrivatePdfStore(Path(settings.source_storage_root))
    )


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


class AdminRevisionView(MaterialDetail):
    source_id: UUID
    status: str
    error_code: str | None
    decision: str | None
    sha256: str


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


def _latest_decision_id(revision_id: UUID | None = None):
    query = select(func.max(SourceDecision.event_id)).where(
        SourceDecision.revision_id == SourceRevision.id
    )
    if revision_id is not None:
        query = query.where(SourceDecision.revision_id == revision_id)
    return query.correlate(SourceRevision).scalar_subquery()


async def _detail(
    session: AsyncSession, revision: SourceRevision
) -> tuple[MaterialView, list[SegmentView]]:
    source = await session.get(Source, revision.source_id)
    if source is None:
        raise HTTPException(404, "Material unavailable")
    segments = (
        await session.scalars(
            select(SourceSegment)
            .where(SourceSegment.revision_id == revision.id)
            .order_by(SourceSegment.ordinal)
        )
    ).all()
    view = MaterialView(
        revision_id=revision.id,
        title=revision.title,
        creator=revision.creator,
        origin_url=source.origin_url,
        rights_usage_note=revision.rights_note,
        media_type=revision.media_type,
    )
    return view, [
        SegmentView(segment_id=s.id, locator=LocatorView(page=s.page or 1), text=s.text)
        for s in segments
    ]


@admin_router.post("/sources", response_model=IntakeView, status_code=201)
async def upload_source(
    request: Request,
    _: Annotated[Actor, Depends(current_admin)],
    file: Annotated[UploadFile, File()],
    origin_url: Annotated[str, Form(min_length=8, max_length=2000)],
    title: Annotated[str, Form(min_length=1, max_length=500)],
    creator: Annotated[str | None, Form()] = None,
    rights_note: Annotated[str | None, Form(max_length=2000)] = None,
    source_id: Annotated[UUID | None, Form()] = None,
) -> IntakeView:
    factory = _factory(request)
    async with factory.begin() as session:
        repo = SourceRepository(session)
        if source_id is None:
            source = await repo.add_source(origin_url)
        else:
            existing_source = await session.get(Source, source_id)
            if existing_source is None or existing_source.origin_url != origin_url:
                raise HTTPException(404, "Source unavailable")
            source = existing_source
        try:
            stored = _store(request).store(
                source.id,
                file.file,
                filename=file.filename or "",
                claimed_media_type=file.content_type or "",
            )
        except IntakeError as exc:
            raise HTTPException(422, str(exc)) from exc
        revision = await repo.add_revision(
            source.id,
            sha256=stored.sha256,
            byte_size=stored.byte_size,
            media_type="application/pdf",
            storage_key=stored.storage_key,
            title=title,
            creator=creator,
            rights_note=rights_note,
        )
        processing = await session.get(SourceProcessing, revision.id)
        if processing is None:
            processing = SourceProcessing(revision_id=revision.id, state="candidate")
            session.add(processing)
        await session.flush()
        return IntakeView(source_id=source.id, revision_id=revision.id, status=processing.state)


@admin_router.get("/revisions/{revision_id}", response_model=AdminRevisionView)
async def admin_revision(
    request: Request, revision_id: UUID, _: Annotated[Actor, Depends(current_admin)]
) -> AdminRevisionView:
    async with _factory(request)() as session:
        revision = await session.get(SourceRevision, revision_id)
        if revision is None:
            raise HTTPException(404, "Revision unavailable")
        processing = await session.get(SourceProcessing, revision_id)
        decision = await session.scalar(
            select(SourceDecision)
            .where(SourceDecision.revision_id == revision_id)
            .order_by(SourceDecision.event_id.desc())
            .limit(1)
        )
        view, segments = await _detail(session, revision)
        return AdminRevisionView(
            **view.model_dump(),
            source_id=revision.source_id,
            status=processing.state if processing else "candidate",
            error_code=processing.error_code if processing else None,
            decision=decision.kind if decision else None,
            sha256=revision.sha256,
            segments=segments,
        )


@admin_router.get("/sources", response_model=list[AdminSourceView])
async def admin_sources(
    request: Request, _: Annotated[Actor, Depends(current_admin)]
) -> list[AdminSourceView]:
    async with _factory(request)() as session:
        rows = (
            await session.execute(
                select(SourceRevision, Source, SourceProcessing)
                .join(Source, Source.id == SourceRevision.source_id)
                .join(SourceProcessing, SourceProcessing.revision_id == SourceRevision.id)
                .order_by(SourceRevision.captured_at.desc())
                .limit(100)
            )
        ).all()
        result = []
        for revision, source, processing in rows:
            decision = await session.scalar(
                select(SourceDecision.kind)
                .where(SourceDecision.revision_id == revision.id)
                .order_by(SourceDecision.event_id.desc())
                .limit(1)
            )
            result.append(
                AdminSourceView(
                    source_id=source.id,
                    revision_id=revision.id,
                    title=revision.title,
                    origin_url=source.origin_url,
                    status=processing.state,
                    decision=decision,
                )
            )
        return result


@admin_router.post("/revisions/{revision_id}/approve", response_model=AdminRevisionView)
async def approve_revision(
    request: Request,
    revision_id: UUID,
    data: DecisionInput,
    actor: Annotated[Actor, Depends(current_admin)],
) -> AdminRevisionView:
    if not data.sensitivity_cleared or not data.user_text:
        raise HTTPException(422, "User text rights and sensitivity clearance required")
    evidence = urlsplit(data.evidence_url)
    if evidence.scheme != "https" or not evidence.hostname:
        raise HTTPException(422, "HTTPS rights evidence URL required")
    async with _factory(request).begin() as session:
        processing = await session.get(SourceProcessing, revision_id, with_for_update=True)
        if processing is None or processing.state != "review_pending":
            raise HTTPException(409, "Revision is not reviewable")
        repo = SourceRepository(session)
        latest = await session.scalar(
            select(SourceDecision)
            .where(SourceDecision.revision_id == revision_id)
            .order_by(SourceDecision.event_id.desc())
            .limit(1)
        )
        if latest is not None:
            raise HTTPException(409, "Revision already decided")
        await repo.record_decision(
            RevisionDecision(
                revision_id,
                DecisionKind.APPROVE,
                RightsScopes(data.user_text, data.original_file, data.provider_transfer),
                data.sensitivity_cleared,
            ),
            reviewer_id=actor.subject_id,
            reason=data.reason,
            evidence_url=data.evidence_url,
        )
    return await admin_revision(request, revision_id, actor)


@admin_router.post("/revisions/{revision_id}/revoke", response_model=AdminRevisionView)
async def revoke_revision(
    request: Request,
    revision_id: UUID,
    data: RevokeInput,
    actor: Annotated[Actor, Depends(current_admin)],
) -> AdminRevisionView:
    async with _factory(request).begin() as session:
        processing = await session.get(SourceProcessing, revision_id, with_for_update=True)
        if processing is None:
            raise HTTPException(404, "Revision unavailable")
        repo = SourceRepository(session)
        latest = await session.scalar(
            select(SourceDecision)
            .where(SourceDecision.revision_id == revision_id)
            .order_by(SourceDecision.event_id.desc())
            .limit(1)
        )
        if latest is None or latest.kind != "approve":
            raise HTTPException(409, "Revision is not approved")
        await repo.record_decision(
            RevisionDecision(revision_id, DecisionKind.REVOKE, RightsScopes(), False),
            reviewer_id=actor.subject_id,
            reason=data.reason,
            evidence_url=latest.evidence_url,
        )
    return await admin_revision(request, revision_id, actor)


@admin_router.post("/revisions/{revision_id}/retry", response_model=AdminRevisionView)
async def retry_revision(
    request: Request,
    revision_id: UUID,
    _: Annotated[Actor, Depends(current_admin)],
) -> AdminRevisionView:
    async with _factory(request).begin() as session:
        record = await session.get(SourceProcessing, revision_id, with_for_update=True)
        if record is None:
            raise HTTPException(404, "Revision unavailable")
        if record.state != "failed":
            raise HTTPException(409, "Only failed processing can be retried")
        record.state = "candidate"
        record.error_code = None
    return await admin_revision(request, revision_id, _)


def _visible_query():
    return (
        select(SourceRevision)
        .join(SourceProcessing, SourceProcessing.revision_id == SourceRevision.id)
        .join(SourceDecision, SourceDecision.revision_id == SourceRevision.id)
        .where(
            SourceProcessing.state == "review_pending",
            SourceDecision.event_id == _latest_decision_id(),
            SourceDecision.kind == "approve",
            SourceDecision.user_text.is_(True),
            SourceDecision.sensitivity_cleared.is_(True),
        )
    )


@materials_router.get("", response_model=list[MaterialView])
async def materials_list(
    request: Request, _: Annotated[Actor, Depends(current_user)]
) -> list[MaterialView]:
    async with _factory(request)() as session:
        revisions = (
            await session.scalars(_visible_query().order_by(SourceRevision.captured_at))
        ).all()
        return [(await _detail(session, revision))[0] for revision in revisions]


@materials_router.get("/{revision_id}", response_model=MaterialDetail)
async def material_detail(
    request: Request, revision_id: UUID, _: Annotated[Actor, Depends(current_user)]
) -> MaterialDetail:
    async with _factory(request)() as session:
        revision = await session.scalar(_visible_query().where(SourceRevision.id == revision_id))
        if revision is None:
            raise HTTPException(404, "Material unavailable")
        view, segments = await _detail(session, revision)
        return MaterialDetail(**view.model_dump(), segments=segments)
