"""Exercise the built HTTP, worker, Qdrant and Yandex text path with invented text.

Requires an isolated Compose project, its first admin, and LIVE_BASE_URL,
LIVE_VECTOR_URL, LIVE_ADMIN_USER, LIVE_ADMIN_PASSWORD in the local environment.
The model key stays in the backend container. No cultural source is used.
"""

import os
import time
from uuid import uuid4

import httpx

from app.infrastructure.vector.text_vectors import COLLECTION


def required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Set {name} for the isolated live check")
    return value


def expect(response: httpx.Response, status: int) -> dict:
    if response.status_code != status:
        raise AssertionError(f"HTTP {response.status_code}, expected {status}")
    return response.json() if response.content else {}


def main() -> None:
    base = required("LIVE_BASE_URL").rstrip("/")
    vector = required("LIVE_VECTOR_URL").rstrip("/")
    admin_name = required("LIVE_ADMIN_USER")
    admin_password = required("LIVE_ADMIN_PASSWORD")
    origin = base
    marker = uuid4().hex[:12]
    user_name = f"synthetic-{marker}"
    user_password = f"synthetic-password-{marker}"
    with (
        httpx.Client(base_url=base, timeout=30, trust_env=False) as admin,
        httpx.Client(base_url=base, timeout=30, trust_env=False) as user,
        httpx.Client(base_url=vector, timeout=10, trust_env=False) as qdrant,
    ):
        login = expect(
            admin.post(
                "/api/v1/auth/login",
                headers={"Origin": origin},
                json={"username": admin_name, "password": admin_password},
            ),
            200,
        )
        admin_headers = {"Origin": origin, "X-CSRF-Token": login["csrf_token"]}
        expect(
            admin.post(
                "/api/v1/admin/accounts",
                headers=admin_headers,
                json={"username": user_name, "password": user_password, "role": "user"},
            ),
            201,
        )
        login = expect(
            user.post(
                "/api/v1/auth/login",
                headers={"Origin": origin},
                json={"username": user_name, "password": user_password},
            ),
            200,
        )
        user_headers = {"Origin": origin, "X-CSRF-Token": login["csrf_token"]}
        chat_id = expect(user.post("/api/v1/chats", headers=user_headers), 201)["id"]
        document = b"The self-authored synthetic swatch is blue.\n"
        intake = expect(
            admin.post(
                "/api/v1/admin/sources",
                headers=admin_headers,
                data={
                    "origin_url": f"https://example.invalid/{marker}",
                    "title": "Self-authored synthetic swatch",
                    "rights_note": "Self-authored synthetic text for this test",
                },
                files={"file": ("swatch.txt", document, "text/plain")},
            ),
            201,
        )
        revision_id = intake["revision_id"]
        assert user.get(f"/api/v1/materials/{revision_id}").status_code == 404
        no_evidence = expect(
            user.post(
                f"/api/v1/chats/{chat_id}/messages",
                headers=user_headers,
                json={
                    "request_id": str(uuid4()),
                    "text": f"Find {marker} before approval",
                },
            ),
            200,
        )
        assert no_evidence["evidence_status"] == "insufficient"
        detail = None
        for _ in range(60):
            detail = expect(admin.get(f"/api/v1/admin/revisions/{revision_id}"), 200)
            if detail["status"] == "review_pending":
                break
            time.sleep(1)
        assert detail is not None and detail["status"] == "review_pending"
        segment_id = detail["segments"][0]["segment_id"]
        expect(
            admin.post(
                f"/api/v1/admin/revisions/{revision_id}/approve",
                headers=admin_headers,
                json={
                    "reason": "Self-authored fixture with test-only transfer consent",
                    "evidence_url": "https://example.invalid/synthetic-rights",
                    "user_text": True,
                    "original_file": False,
                    "provider_transfer": True,
                    "sensitivity_cleared": True,
                },
            ),
            200,
        )
        for _ in range(120):
            point = qdrant.get(f"/collections/{COLLECTION}/points/{segment_id}")
            if point.status_code == 200:
                break
            time.sleep(1)
        assert point.status_code == 200
        turn = expect(
            user.post(
                f"/api/v1/chats/{chat_id}/messages",
                headers=user_headers,
                json={
                    "request_id": str(uuid4()),
                    "text": "Suggest one new color concept from the synthetic swatch; quote the fact exactly.",
                },
            ),
            200,
        )
        assert turn["evidence_status"] == "grounded"
        assert len(turn["citations"]) == 1
        assert turn["citations"][0]["revision_id"] == revision_id
        assert turn["citations"][0]["segment_id"] == segment_id
        print("live_yandex_grounded", "citation_exact", True)
        expect(
            admin.post(
                f"/api/v1/admin/revisions/{revision_id}/revoke",
                headers=admin_headers,
                json={"reason": "End of self-authored synthetic transfer check"},
            ),
            200,
        )
        assert user.get(f"/api/v1/materials/{revision_id}").status_code == 404
        historical = expect(user.get(f"/api/v1/chats/{chat_id}"), 200)
        assert historical["turns"][-1]["citations"][0]["available"] is False
        print("live_yandex_revocation", "citation_unavailable", True)


if __name__ == "__main__":
    main()
