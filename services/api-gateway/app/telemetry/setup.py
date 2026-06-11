"""
API Gateway — telemetry bootstrap.

Provides:
  - OpenTelemetry tracer with OTLP export
  - OTel gRPC client interceptor factory (injects W3C TraceContext into outgoing calls)
  - Prometheus FastAPI Instrumentator (auto-instruments all routes)
  - /metrics endpoint mounted on the FastAPI app
"""
from __future__ import annotations

import logging
import os

from opentelemetry import trace, propagate
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.propagate import inject
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

logger = logging.getLogger(__name__)


def setup_tracing(service_name: str = "api-gateway") -> trace.Tracer:
    """Initialise the global TracerProvider for the API Gateway."""
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
    resource  = Resource.create({SERVICE_NAME: service_name})
    provider  = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True))
    )
    trace.set_tracer_provider(provider)
    propagate.set_global_textmap(TraceContextTextMapPropagator())
    logger.info("OTel tracing configured for '%s', exporting to %s", service_name, endpoint)
    return trace.get_tracer(service_name)


def make_grpc_metadata_with_trace() -> list[tuple[str, str]]:
    """
    Inject the current OTel span context into gRPC metadata as W3C TraceContext headers.
    Call this when building gRPC requests from the API Gateway so that downstream
    gRPC services can extract and continue the trace.
    """
    carrier: dict[str, str] = {}
    inject(carrier)
    return [(k, v) for k, v in carrier.items()]


def instrument_fastapi(app) -> None:
    """
    Attach Prometheus FastAPI Instrumentator and mount /metrics.
    Must be called after all routes are registered.
    """
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
        Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            should_respect_env_var=False,
            excluded_handlers=["/metrics", "/health"],
            body_handlers=[],
        ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
        logger.info("Prometheus /metrics endpoint mounted on FastAPI")
    except ImportError:
        logger.warning("prometheus_fastapi_instrumentator not installed; /metrics unavailable")
