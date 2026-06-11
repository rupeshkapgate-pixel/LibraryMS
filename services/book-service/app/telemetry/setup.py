"""
Shared telemetry bootstrap for gRPC services.

Provides:
  - OpenTelemetry tracer with OTLP gRPC export
  - Prometheus metrics: request counter, latency histogram, in-flight gauge
  - HTTP /metrics endpoint served on a separate port (default 9090)
  - gRPC server interceptor that records both OTel spans and Prometheus metrics
"""
from __future__ import annotations

import logging
import os
import time
import threading
from typing import Callable

import grpc

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.propagate import extract

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from http.server import HTTPServer, BaseHTTPRequestHandler

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


# ── OpenTelemetry setup ───────────────────────────────────────────────────────

def setup_tracing(service_name: str) -> trace.Tracer:
    """Initialise the global TracerProvider and return a named tracer."""
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")

    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)

    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)
    logger.info(f"OTel tracing configured for '{service_name}', exporting to {otlp_endpoint}")
    return trace.get_tracer(service_name)


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
    server = HTTPServer(("0.0.0.0", port), _MetricsHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Prometheus /metrics endpoint running on :{port}")


# ── gRPC server interceptor ───────────────────────────────────────────────────

class TelemetryInterceptor(grpc.aio.ServerInterceptor):
    """
    Async gRPC interceptor that:
      1. Extracts W3C TraceContext from incoming metadata and starts a child span.
      2. Records Prometheus metrics (counter, histogram, in-flight gauge).
      3. Tags the span with the gRPC status code on completion.
    """

    def __init__(self, service_name: str):
        self._service = service_name
        self._tracer = trace.get_tracer(service_name)

    async def intercept_service(
        self,
        continuation: Callable,
        handler_call_details: grpc.HandlerCallDetails,
    ):
        return await continuation(handler_call_details)

    async def intercept_unary_unary(self, continuation, client_call_details, request):
        return await self._intercept(continuation, client_call_details, request)

    async def intercept_unary_stream(self, continuation, client_call_details, request):
        return await self._intercept(continuation, client_call_details, request)

    async def intercept_stream_unary(self, continuation, client_call_details, request_iterator):
        return await self._intercept(continuation, client_call_details, request_iterator)

    async def intercept_stream_stream(self, continuation, client_call_details, request_iterator):
        return await self._intercept(continuation, client_call_details, request_iterator)

    async def _intercept(self, continuation, client_call_details, request_or_iter):
        method = client_call_details.method or "unknown"
        # Strip leading slash and replace / with .
        method_short = method.lstrip("/").replace("/", ".")

        # Extract trace context from gRPC metadata
        metadata = dict(client_call_details.metadata or [])
        ctx = extract(metadata)

        GRPC_IN_FLIGHT_GAUGE.labels(service=self._service).inc()
        start = time.perf_counter()
        status_code = "OK"

        with self._tracer.start_as_current_span(
            method_short,
            context=ctx,
            kind=trace.SpanKind.SERVER,
        ) as span:
            span.set_attribute("rpc.system", "grpc")
            span.set_attribute("rpc.service", self._service)
            span.set_attribute("rpc.method", method_short)
            try:
                response = await continuation(client_call_details, request_or_iter)
                return response
            except grpc.RpcError as exc:
                status_code = exc.code().name
                span.set_attribute("rpc.grpc.status_code", status_code)
                span.record_exception(exc)
                raise
            except Exception as exc:
                status_code = "INTERNAL"
                span.record_exception(exc)
                raise
            finally:
                elapsed = time.perf_counter() - start
                GRPC_REQUEST_COUNTER.labels(
                    service=self._service, method=method_short, status=status_code
                ).inc()
                GRPC_LATENCY_HISTOGRAM.labels(
                    service=self._service, method=method_short
                ).observe(elapsed)
                GRPC_IN_FLIGHT_GAUGE.labels(service=self._service).dec()


# ── Convenience bootstrap ─────────────────────────────────────────────────────

def bootstrap(service_name: str, metrics_port: int = 9090) -> trace.Tracer:
    """
    Call once at service startup.
    Initialises OTel tracing, starts Prometheus HTTP server, returns tracer.
    """
    tracer = setup_tracing(service_name)
    start_metrics_server(metrics_port)
    return tracer
