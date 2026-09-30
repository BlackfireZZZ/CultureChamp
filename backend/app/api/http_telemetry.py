"""Metadata-only HTTP timing without client addresses or user-supplied URLs."""

import logging
import time

from fastapi.routing import APIRoute
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("uvicorn.error")
ALLOWED_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"})


async def http_telemetry(request: Request, call_next: RequestResponseEndpoint) -> Response:
    started_ns = time.monotonic_ns()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        matched = request.scope.get("route")
        route = matched.path if isinstance(matched, APIRoute) else "unmatched"
        method = request.method if request.method in ALLOWED_METHODS else "OTHER"
        logger.info(
            "http_call method=%s route=%s status=%d duration_ms=%d",
            method,
            route,
            status,
            (time.monotonic_ns() - started_ns) // 1_000_000,
        )
