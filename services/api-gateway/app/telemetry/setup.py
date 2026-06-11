"""
API Gateway telemetry bootstrap.

Provides:
  - OpenTelemetry SDK TracerProvider with OTLP gRPC export to Jaeger
  - FastAPI instrumentation for HTTP spans
  - gRPC aio client instrumentation for outbound RPC spans
  - explicit W3C TraceContext metadata injection for downstream gRPC calls
  - Prometheus FastAPI /metrics endpoint
"""
from __future__ import annotations

import logging
import os

from opentelemetry import propagate, trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.propagate import inject
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import ProxyTracerProvider
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

logger = logging.getLogger(__name__)

_TRACING_CONFIGURED = False
_FASTAPI_INSTRUMENTED = False
_GRPC_CLIENT_INSTRUMENTED = False
_PROMETHEUS_EXPOSED = False


def setup_tracing(service_name: str = "api-gateway") -> trace.Tracer:
    """Initialise OpenTelemetry SDK and OTLP exporter once per process."""
    global _TRACING_CONFIGURED

    if _TRACING_CONFIGURED:
        return trace.get_tracer(service_name)

    current_provider = trace.get_tracer_provider()
    if isinstance(current_provider, ProxyTracerProvider):
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4317")
        resource = Resource.create(
            {
                SERVICE_NAME: service_name,
                "deployment.environment": os.getenv("ENVIRONMENT", "local"),
            }
        )
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True))
        )
        trace.set_tracer_provider(provider)
    else:
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "already-configured")

    propagate.set_global_textmap(TraceContextTextMapPropagator())
    _TRACING_CONFIGURED = True
    logger.info(
        "OTel tracing configured for '%s', exporting to %s",
        service_name,
        endpoint,
    )
    return trace.get_tracer(service_name)


def instrument_grpc_client() -> None:
    """Instrument grpc.aio clients so outbound gRPC calls create client spans."""
    global _GRPC_CLIENT_INSTRUMENTED
    if _GRPC_CLIENT_INSTRUMENTED:
        return
    try:
        from opentelemetry.instrumentation.grpc import GrpcAioInstrumentorClient

        GrpcAioInstrumentorClient().instrument()
        _GRPC_CLIENT_INSTRUMENTED = True
        logger.info("OpenTelemetry gRPC aio client instrumentation enabled")
    except Exception as exc:  # pragma: no cover - defensive startup logging
        logger.warning("gRPC client instrumentation unavailable: %s", exc)


def make_grpc_metadata_with_trace(
    existing: list[tuple[str, str]] | None = None,
) -> list[tuple[str, str]]:
    """
    Inject current W3C TraceContext into gRPC metadata.

    Keep existing metadata such as x-correlation-id, then add traceparent/tracestate
    from the active FastAPI span. This lets downstream gRPC services continue the
    same Jaeger trace.
    """
    metadata: list[tuple[str, str]] = list(existing or [])
    carrier: dict[str, str] = {}
    inject(carrier)
    metadata.extend((key, value) for key, value in carrier.items())
    return metadata


def instrument_fastapi(app) -> None:
    """Attach FastAPI tracing and expose Prometheus metrics."""
    global _FASTAPI_INSTRUMENTED, _PROMETHEUS_EXPOSED

    if not _FASTAPI_INSTRUMENTED:
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            FastAPIInstrumentor.instrument_app(
                app,
                excluded_urls="/metrics,/health",
            )
            _FASTAPI_INSTRUMENTED = True
            logger.info("OpenTelemetry FastAPI instrumentation enabled")
        except Exception as exc:  # pragma: no cover - defensive startup logging
            logger.warning("FastAPI instrumentation unavailable: %s", exc)

    if not _PROMETHEUS_EXPOSED:
        try:
            from prometheus_fastapi_instrumentator import Instrumentator

            Instrumentator(
                should_group_status_codes=True,
                should_ignore_untemplated=True,
                should_respect_env_var=False,
                excluded_handlers=["/metrics", "/health"],
                body_handlers=[],
            ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
            _PROMETHEUS_EXPOSED = True
            logger.info("Prometheus /metrics endpoint mounted on FastAPI")
        except ImportError:
            logger.warning("prometheus_fastapi_instrumentator not installed; /metrics unavailable")
