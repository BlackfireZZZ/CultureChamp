import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


def test_liveness() -> None:
    async def request() -> None:
        transport = ASGITransport(app=create_app())
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/health/live")
        assert response.status_code == 200
        assert response.json() == {"status": "alive"}

    asyncio.run(request())


def test_http_telemetry_uses_route_template_without_request_data(
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def request() -> None:
        transport = ASGITransport(app=create_app())
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            assert (await client.get("/api/v1/health/live?secret-canary=1")).status_code == 200
            assert (
                await client.get("/api/v1/materials/private-path-canary?secret-canary=1")
            ).status_code == 401
            assert (await client.get("/private-path-canary")).status_code == 404

    with caplog.at_level("INFO", logger="uvicorn.error"):
        asyncio.run(request())
    assert "http_call method=GET route=/health/live status=200" in caplog.text
    assert "http_call method=GET route=/materials/{revision_id} status=401" in caplog.text
    assert "http_call method=GET route=unmatched status=404" in caplog.text
    assert "secret-canary" not in caplog.text
    assert "private-path-canary" not in caplog.text
