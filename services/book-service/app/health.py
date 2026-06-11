"""
gRPC Health Checking (grpc_health_v1) implementation.

Implements the standard gRPC Health Checking Protocol:
  https://github.com/grpc/grpc/blob/master/doc/health-checking.md

Each service registers its servicer name in the HealthServicer so that
liveness and readiness probes (kubectl, load balancers, service meshes)
can interrogate health via:
  grpc_health_probe -addr=:PORT -service=<service_name>
"""
from __future__ import annotations

import logging

from grpc_health.v1 import health_pb2, health_pb2_grpc
from grpc_health.v1.health import HealthServicer as _BaseHealthServicer

logger = logging.getLogger(__name__)


class LivenessHealthServicer(_BaseHealthServicer):
    """
    Wraps the standard HealthServicer and exposes two helper methods:
      - mark_serving(service)   → sets status to SERVING
      - mark_not_serving(service) → sets status to NOT_SERVING
    """

    def __init__(self):
        super().__init__()
        # The empty string "" represents overall server health
        self.set("", health_pb2.HealthCheckResponse.SERVING)

    def mark_serving(self, service: str) -> None:
        self.set(service, health_pb2.HealthCheckResponse.SERVING)
        logger.info(f"Health: {service or '(overall)'} → SERVING")

    def mark_not_serving(self, service: str) -> None:
        self.set(service, health_pb2.HealthCheckResponse.NOT_SERVING)
        logger.warning(f"Health: {service or '(overall)'} → NOT_SERVING")


def add_health_servicer(server, service_names: list[str]) -> LivenessHealthServicer:
    """
    Register a LivenessHealthServicer on *server* and mark every service
    name in *service_names* as SERVING.

    Returns the servicer so the caller can later call mark_not_serving()
    during graceful shutdown.

    Usage in main.py:
        health_svc = add_health_servicer(server, ["book.BookService"])
        # … at shutdown:
        health_svc.mark_not_serving("book.BookService")
    """
    health_servicer = LivenessHealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)

    for name in service_names:
        health_servicer.mark_serving(name)

    return health_servicer
