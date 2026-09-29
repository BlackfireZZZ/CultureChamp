from fastapi import APIRouter, HTTPException, status

from app.application.health import check_readiness
from app.infrastructure.db.health import DatabaseReadinessProbe
from app.infrastructure.db.session import engine

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", operation_id="health_live")
async def liveness() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/ready", operation_id="health_ready")
async def readiness() -> dict[str, str]:
    if not await check_readiness(DatabaseReadinessProbe(engine)):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Not ready")
    return {"status": "ready"}
