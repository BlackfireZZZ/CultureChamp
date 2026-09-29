import asyncio

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
