"""Structured JSON logging and correlation-id helpers."""
from __future__ import annotations

import contextvars
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

import grpc

_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="-")
_SERVICE_NAME = "unknown-service"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "service": getattr(record, "service", _SERVICE_NAME),
            "operation": getattr(record, "operation", record.name),
            "correlation_id": getattr(record, "correlation_id", get_correlation_id()),
            "message": record.getMessage(),
        }
        error = getattr(record, "error", None)
        if error:
            payload["error"] = str(error)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        reserved = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread", "threadName",
            "processName", "process", "message", "asctime", "service",
            "operation", "correlation_id", "error",
        }
        for key, value in record.__dict__.items():
            if key not in reserved and key not in payload and value is not None:
                payload[key] = value
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_json_logging(service_name: str, level: str = "INFO") -> None:
    global _SERVICE_NAME
    _SERVICE_NAME = service_name
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))


def set_correlation_id(correlation_id: str) -> None:
    _correlation_id.set(correlation_id or "-")


def get_correlation_id() -> str:
    return _correlation_id.get()


def grpc_metadata_from_correlation_id(correlation_id: str | None = None) -> list[tuple[str, str]]:
    cid = correlation_id or get_correlation_id()
    return [("x-correlation-id", cid)] if cid and cid != "-" else []


def get_grpc_correlation_id(context: grpc.aio.ServicerContext | None) -> str:
    if context is None:
        return "-"
    try:
        metadata = dict(context.invocation_metadata() or [])
    except Exception:
        return "-"
    return metadata.get("x-correlation-id") or metadata.get("correlation-id") or "-"


def log_event(
    logger: logging.Logger,
    level: int,
    *,
    service: str,
    operation: str,
    message: str,
    correlation_id: str | None = None,
    error: Exception | str | None = None,
    **extra: Any,
) -> None:
    extra_payload = {
        "service": service,
        "operation": operation,
        "correlation_id": correlation_id or get_correlation_id(),
        **extra,
    }
    if error is not None:
        extra_payload["error"] = str(error)
    logger.log(level, message, extra=extra_payload)
