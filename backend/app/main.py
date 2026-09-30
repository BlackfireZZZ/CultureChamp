from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.api.routes.health import router as health_router
from app.api.routes.identity import admin_account_router, auth_router
from app.api.routes.sources import admin_router, materials_router
from app.application.identity import IdentityService
from app.application.source_management import SourceConflict, SourceInputError, SourceNotFound
from app.core.config import settings
from app.infrastructure.db.identity_store import SqlIdentityStore
from app.infrastructure.db.session import engine, session_factory
from app.infrastructure.passwords import Argon2PasswordCodec


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    identity_store = SqlIdentityStore(session_factory)
    codec = Argon2PasswordCodec()
    app.state.session_store = identity_store
    app.state.identity_service = IdentityService(identity_store, codec, codec.dummy_hash)
    app.state.source_session_factory = session_factory

    @app.exception_handler(SourceNotFound)
    async def source_not_found(_: Request, __: SourceNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": "Material unavailable"})

    @app.exception_handler(SourceConflict)
    async def source_conflict(_: Request, exc: SourceConflict) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(SourceInputError)
    async def source_input_error(_: Request, exc: SourceInputError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(admin_account_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    app.include_router(materials_router, prefix="/api/v1")
    return app


app = create_app()
