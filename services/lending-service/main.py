"""Lending Service gRPC Server with standard gRPC health checking."""
import asyncio
import logging
import os
import signal

import grpc
from grpc_health.v1 import health_pb2_grpc, health_pb2
from grpc_health.v1.health import HealthServicer

from app.grpc_handlers.lending_handler import LendingServiceHandler
from app.proto_generated import lending_pb2_grpc
from app.database import engine
from app.models.lending import Base
import sqlalchemy

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

HOST = os.getenv("GRPC_HOST", "0.0.0.0")
PORT = int(os.getenv("GRPC_PORT", "50053"))


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.execute(sqlalchemy.text("CREATE SCHEMA IF NOT EXISTS lending_db"))
        await conn.execute(sqlalchemy.text(
            "DO $$ BEGIN "
            "CREATE TYPE lending_db.lendingstatus AS ENUM ('BORROWED','RETURNED','OVERDUE'); "
            "EXCEPTION WHEN duplicate_object THEN null; END $$;"
        ))
        await conn.run_sync(Base.metadata.create_all)
    logger.info("lending_db schema ready")


async def serve() -> None:
    await init_db()

    server = grpc.aio.server(options=[
        ("grpc.max_send_message_length",   50 * 1024 * 1024),
        ("grpc.max_receive_message_length", 50 * 1024 * 1024),
    ])

    lending_pb2_grpc.add_LendingServiceServicer_to_server(LendingServiceHandler(), server)

    health_servicer = HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    health_servicer.set("lending.LendingService", health_pb2.HealthCheckResponse.SERVING)
    health_servicer.set("",                       health_pb2.HealthCheckResponse.SERVING)

    listen_addr = f"{HOST}:{PORT}"
    server.add_insecure_port(listen_addr)
    await server.start()
    logger.info("Lending Service listening on %s", listen_addr)

    async def _shutdown(*_):
        health_servicer.set("lending.LendingService", health_pb2.HealthCheckResponse.NOT_SERVING)
        await server.stop(grace=5)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(_shutdown()))

    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
