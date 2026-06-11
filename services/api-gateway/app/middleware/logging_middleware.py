"""Middleware for API Gateway."""
import logging
import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.observability.logging import log_event, set_correlation_id

logger = logging.getLogger(__name__)
_SERVICE = "api-gateway"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID") or request.headers.get("x-correlation-id") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        set_correlation_id(correlation_id)

        start_time = time.time()
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            process_time = (time.time() - start_time) * 1000
            log_event(
                logger,
                logging.ERROR,
                service=_SERVICE,
                operation="http_request",
                message="HTTP request failed",
                correlation_id=correlation_id,
                error=exc,
                method=request.method,
                path=request.url.path,
                status=500,
                duration_ms=round(process_time, 2),
            )
            raise

        process_time = (time.time() - start_time) * 1000
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

        level = logging.ERROR if response.status_code >= 500 else logging.WARNING if response.status_code >= 400 else logging.INFO
        log_event(
            logger,
            level,
            service=_SERVICE,
            operation="http_request",
            message="HTTP request completed",
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(process_time, 2),
        )
        return response
