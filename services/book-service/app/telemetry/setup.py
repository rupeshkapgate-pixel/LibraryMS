"""
Shared telemetry bootstrap for gRPC services.

Provides:
  - OpenTelemetry SDK TracerProvider with OTLP gRPC export to Jaeger
  - gRPC aio server instrumentation for inbound RPC spans
  - gRPC aio client instrumentation for outbound RPC spans
  - W3C TraceContext extraction/injection helpers
  - Prometheus metrics: request counter, latency histogram, in-flight gauge, DB counters
  - HTTP /metrics endpoint served on a separate port
"""
from __future__ import annotations

import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import grpc
from opentelemetry import propagate, trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.propagate import extract, inject
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import ProxyTracerProvider
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

logger = logging.getLogger(__name__)

# ── Prometheus metrics (module-level singletons) ──────────────────────────────

GRPC_REQUEST_COUNTER = Counter(
    "grpc_server_requests_total",
    "Total gRPC requests",
    ["service", "method", "status"],
)

GRPC_LATENCY_HISTOGRAM = Histogram(
    "grpc_server_request_duration_seconds",
    "gRPC request latency in seconds",
    ["service", "method"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

GRPC_IN_FLIGHT_GAUGE = Gauge(
    "grpc_server_requests_in_flight",
    "Currently in-flight gRPC requests",
    ["service"],
)

DB_QUERY_COUNTER = Counter(
    "db_queries_total",
    "Total database queries",
    ["service", "operation", "status"],
)

DB_QUERY_LATENCY = Histogram(
    "db_query_duration_seconds",
    "Database query latency in seconds",
    ["service", "operation"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)

_TRACING_CONFIGURED = False
_GRPC_SERVER_INSTRUMENTED = False
_GRPC_CLIENT_INSTRUMENTED = False
_METRICS_SERVER_STARTED = False


# ── OpenTelemetry setup ───────────────────────────────────────────────────────

def setup_tracing(service_name: str) -> trace.Tracer:
    """Initialise OpenTelemetry SDK and OTLP exporter once per process."""
    global _TRACING_CONFIGURED

    if _TRACING_CONFIGURED:
        return trace.get_tracer(service_name)

    current_provider = trace.get_tracer_provider()
    if isinstance(current_provider, ProxyTracerProvider):
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4317")
        resource = Resource.create(
            {
                SERVICE_NAME: service_name,
                "deployment.environment": os.getenv("ENVIRONMENT", "local"),
            }
        )
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
    else:
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "already-configured")

    propagate.set_global_textmap(TraceContextTextMapPropagator())
    _TRACING_CONFIGURED = True
    logger.info("OTel tracing configured for '%s', exporting to %s", service_name, otlp_endpoint)
    return trace.get_tracer(service_name)


def instrument_grpc_server() -> None:
    """Instrument grpc.aio server so inbound RPCs appear in Jaeger."""
    global _GRPC_SERVER_INSTRUMENTED
    if _GRPC_SERVER_INSTRUMENTED:
        return
    try:
        from opentelemetry.instrumentation.grpc import GrpcAioInstrumentorServer

        GrpcAioInstrumentorServer().instrument()
        _GRPC_SERVER_INSTRUMENTED = True
        logger.info("OpenTelemetry gRPC aio server instrumentation enabled")
    except Exception as exc:  # pragma: no cover - defensive startup logging
        logger.warning("gRPC server instrumentation unavailable: %s", exc)


def instrument_grpc_client() -> None:
    """Instrument grpc.aio clients so outbound RPCs appear in Jaeger."""
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
    """Inject current W3C TraceContext into outgoing gRPC metadata."""
    metadata: list[tuple[str, str]] = list(existing or [])
    carrier: dict[str, str] = {}
    inject(carrier)
    metadata.extend((key, value) for key, value in carrier.items())
    return metadata


def extract_context_from_metadata(metadata: list[tuple[str, str]] | tuple[tuple[str, str], ...] | None):
    """Extract W3C TraceContext from gRPC metadata."""
    return extract(dict(metadata or []))


# ── Prometheus HTTP server ────────────────────────────────────────────────────

class _MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path == "/metrics":
            output = generate_latest()
            self.send_response(200)
            self.send_header("Content-Type", CONTENT_TYPE_LATEST)
            self.send_header("Content-Length", str(len(output)))
            self.end_headers()
            self.wfile.write(output)
        elif self.path in ("/health", "/"):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):  # silence access log
        pass


def start_metrics_server(port: int = 9090) -> None:
    """Start the Prometheus scrape endpoint on a background thread."""
    global _METRICS_SERVER_STARTED
    if _METRICS_SERVER_STARTED:
        return
    server = HTTPServer(("0.0.0.0", port), _MetricsHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _METRICS_SERVER_STARTED = True
    logger.info("Prometheus /metrics endpoint running on :%s", port)


# ── Legacy interceptor retained for compatibility ────────────────────────────

class TelemetryInterceptor(grpc.aio.ServerInterceptor):
    """
    Compatibility interceptor.

    Official OpenTelemetry gRPC aio instrumentation is now enabled through
    instrument_grpc_server(). This interceptor is kept so older imports/tests do
    not break, but it simply delegates to grpc.aio normally.
    """

    def __init__(self, service_name: str):
        self._service = service_name

    async def intercept_service(self, continuation, handler_call_details):
        return await continuation(handler_call_details)


# ── Convenience bootstrap ─────────────────────────────────────────────────────

def bootstrap(service_name: str, metrics_port: int = 9090, instrument_client: bool = False) -> trace.Tracer:
    """
    Call once at service startup.

    Initialises OTel tracing, gRPC server instrumentation, optional gRPC client
    instrumentation, and starts the Prometheus HTTP endpoint.
    """
    tracer = setup_tracing(service_name)
    instrument_grpc_server()
    if instrument_client:
        instrument_grpc_client()
    start_metrics_server(metrics_port)
    return tracer
