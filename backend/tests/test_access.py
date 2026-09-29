from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.auth import SESSION_COOKIE, current_admin, current_session, current_user
from app.application.access import (
    Actor,
    HiddenResource,
    Role,
    Session,
    require_owner,
    require_visible_revision,
)


class FakeSessions:
    def __init__(self) -> None:
        future = datetime.now(UTC) + timedelta(hours=1)
        past = datetime.now(UTC) - timedelta(seconds=1)
        issued = datetime.now(UTC) - timedelta(minutes=1)
        self.sessions = {
            "user-token": Session(Actor("user-1", Role.USER), issued, future, "csrf-user"),
            "admin-token": Session(Actor("admin-1", Role.ADMIN), issued, future, "csrf-admin"),
            "expired-token": Session(Actor("user-1", Role.USER), issued, past, "csrf-old"),
            "overlong-token": Session(
                Actor("user-1", Role.USER), issued, issued + timedelta(hours=13), "csrf-long"
            ),
        }

    async def find(self, token: str) -> Session | None:
        return self.sessions.get(token)


def test_direct_api_roles_and_expiry() -> None:
    app = FastAPI()
    app.state.session_store = FakeSessions()

    @app.get("/user")
    def user_route(actor: Annotated[Actor, Depends(current_user)]) -> dict[str, str]:
        return {"id": actor.subject_id}

    @app.get("/admin")
    def admin_route(actor: Annotated[Actor, Depends(current_admin)]) -> dict[str, str]:
        return {"id": actor.subject_id}

    with TestClient(app) as client:
        assert client.get("/user").status_code == 401
        client.cookies.set(SESSION_COOKIE, "expired-token")
        assert client.get("/user").status_code == 401
        client.cookies.set(SESSION_COOKIE, "overlong-token")
        assert client.get("/user").status_code == 401
        client.cookies.set(SESSION_COOKIE, "user-token")
        assert client.get("/user").json() == {"id": "user-1"}
        assert client.get("/admin").status_code == 403
        client.cookies.set(SESSION_COOKIE, "admin-token")
        assert client.get("/admin").json() == {"id": "admin-1"}
        assert client.get("/user").status_code == 403


def test_unsafe_api_requires_same_origin_and_csrf() -> None:
    app = FastAPI()
    app.state.session_store = FakeSessions()

    @app.post("/write")
    def write_route(_: Annotated[Session, Depends(current_session)]) -> dict[str, bool]:
        return {"ok": True}

    with TestClient(app, base_url="https://example.test") as client:
        client.cookies.set(SESSION_COOKIE, "user-token")
        assert client.post("/write").status_code == 403
        assert (
            client.post(
                "/write", headers={"origin": "https://evil.test", "x-csrf-token": "csrf-user"}
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/write", headers={"origin": "https://example.test", "x-csrf-token": "wrong"}
            ).status_code
            == 403
        )
        assert client.post(
            "/write", headers={"origin": "https://example.test", "x-csrf-token": "csrf-user"}
        ).json() == {"ok": True}


def test_guessed_chat_and_revision_ids_are_hidden() -> None:
    user = Actor("user-1", Role.USER)
    admin = Actor("admin-1", Role.ADMIN)
    for owner in ("user-2", "unknown"):
        try:
            require_owner(user, owner)
        except HiddenResource:
            pass
        else:
            raise AssertionError("foreign chat was visible")
    for flags in ((False, False, True), (True, True, True), (True, False, False)):
        try:
            require_visible_revision(
                user, approved=flags[0], revoked=flags[1], rights_permitted=flags[2]
            )
        except HiddenResource:
            pass
        else:
            raise AssertionError("hidden revision was visible")
    require_visible_revision(admin, approved=False, revoked=False, rights_permitted=False)
