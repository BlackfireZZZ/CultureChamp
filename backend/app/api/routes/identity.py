"""Session and invite-only account transport contracts."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from app.api.auth import (
    current_admin,
    current_session,
    get_identity_service,
    require_allowed_origin,
    session_cookie_name,
)
from app.application.access import Actor, Role, Session
from app.application.identity import (
    IdentityService,
    InvalidAccountInput,
    InvalidCredentials,
    LoginThrottled,
)
from app.core.config import settings

auth_router = APIRouter(prefix="/auth", tags=["auth"])
admin_account_router = APIRouter(prefix="/admin/accounts", tags=["admin"])


class AccountView(BaseModel):
    id: str
    username: str
    role: Role


class AuthView(BaseModel):
    user: AccountView
    csrf_token: str


class LoginInput(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class CreateAccountInput(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=12, max_length=128)
    role: Role = Role.USER


def _auth_view(session: Session) -> AuthView:
    actor = session.actor
    return AuthView(
        user=AccountView(
            id=actor.subject_id,
            username=actor.username or "",
            role=actor.role,
        ),
        csrf_token=session.csrf_token,
    )


@auth_router.post("/login", response_model=AuthView)
async def login(
    data: LoginInput,
    request: Request,
    response: Response,
    service: Annotated[IdentityService, Depends(get_identity_service)],
) -> AuthView:
    require_allowed_origin(request)
    try:
        result = await service.login(data.username, data.password)
    except LoginThrottled as exc:
        raise HTTPException(status_code=429, detail="Login temporarily unavailable") from exc
    except InvalidCredentials as exc:
        raise HTTPException(status_code=401, detail="Invalid credentials") from exc
    previous_token = request.cookies.get(session_cookie_name())
    if previous_token:
        await service.logout(previous_token)
    response.set_cookie(
        session_cookie_name(),
        result.token,
        path="/",
        httponly=True,
        secure=settings.app_env != "development",
        samesite="strict",
    )
    return _auth_view(result.session)


@auth_router.get("/me", response_model=AuthView)
async def me(session: Annotated[Session, Depends(current_session)]) -> AuthView:
    return _auth_view(session)


@auth_router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    _: Annotated[Session, Depends(current_session)],
    service: Annotated[IdentityService, Depends(get_identity_service)],
) -> None:
    token = request.cookies.get(session_cookie_name())
    if token is not None:
        await service.logout(token)
    response.delete_cookie(session_cookie_name(), path="/")


@admin_account_router.post("", response_model=AccountView, status_code=201)
async def create_account(
    data: CreateAccountInput,
    actor: Annotated[Actor, Depends(current_admin)],
    service: Annotated[IdentityService, Depends(get_identity_service)],
) -> AccountView:
    try:
        account = await service.create_account(actor, data.username, data.password, data.role)
    except InvalidAccountInput as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Account already exists") from exc
    return AccountView(id=str(account.id), username=account.username, role=account.role)
