from secrets import compare_digest
from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request

from app.application.access import Actor, Role, Session, SessionStore
from app.application.identity import IdentityService
from app.core.config import settings

SESSION_COOKIE = "culturechamp-dev-session"
PRODUCTION_SESSION_COOKIE = "__Host-culturechamp-session"
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def session_cookie_name() -> str:
    return PRODUCTION_SESSION_COOKIE if settings.app_env != "development" else SESSION_COOKIE


def _same_origin(request: Request) -> bool:
    origin = request.headers.get("origin")
    if not origin:
        return False
    allowed = {str(request.base_url).rstrip("/"), *settings.backend_cors_origins}
    return origin.rstrip("/") in allowed


def require_allowed_origin(request: Request) -> None:
    if not _same_origin(request):
        raise HTTPException(status_code=403, detail="Request forbidden")


def get_identity_service(request: Request) -> IdentityService:
    service = cast("IdentityService | None", getattr(request.app.state, "identity_service", None))
    if service is None:
        raise HTTPException(status_code=503, detail="Authentication unavailable")
    return service


async def current_session(request: Request) -> Session:
    token = request.cookies.get(session_cookie_name())
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    store = cast("SessionStore | None", getattr(request.app.state, "session_store", None))
    if store is None:
        raise HTTPException(status_code=503, detail="Authentication unavailable")
    session = await store.find(token)
    if session is None or not session.is_valid():
        raise HTTPException(status_code=401, detail="Authentication required")
    if request.method in UNSAFE_METHODS:
        supplied = request.headers.get("x-csrf-token")
        if (
            not _same_origin(request)
            or not supplied
            or not compare_digest(supplied, session.csrf_token)
        ):
            raise HTTPException(status_code=403, detail="Request forbidden")
    return session


async def current_user(session: Annotated[Session, Depends(current_session)]) -> Actor:
    if session.actor.role != Role.USER:
        raise HTTPException(status_code=403, detail="Access forbidden")
    return session.actor


async def current_admin(session: Annotated[Session, Depends(current_session)]) -> Actor:
    if session.actor.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Access forbidden")
    return session.actor
