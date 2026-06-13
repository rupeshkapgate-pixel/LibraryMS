"""Lending Service gRPC Server."""
import asyncio
import logging
import os
import signal

import grpc

from app.grpc_handlers.lending_handler import LendingServiceHandler
from app.proto_generated import lending_pb2_grpc
from app.database import engine
from app.observability.logging import configure_json_logging, log_event
from app.telemetry.setup import bootstrap
from app.models.lending import Base
from app.grpc_clients import close_downstream_channels

configure_json_logging("lending-service")
logger = logging.getLogger(__name__)

HOST = os.getenv("GRPC_HOST", "0.0.0.0")
METRICS_PORT = int(os.getenv("METRICS_PORT", "9103"))
PORT = int(os.getenv("GRPC_PORT", "50053"))


async def init_db():
    async with engine.begin() as conn:
        await conn.execute(
            __import__("sqlalchemy").text("CREATE SCHEMA IF NOT EXISTS lending_db")
        )
        await conn.execute(
            __import__("sqlalchemy").text(
                "DO $$ BEGIN "
                "CREATE TYPE lending_db.lendingstatus AS ENUM ('BORROWED', 'RETURNED', 'OVERDUE'); "
                "EXCEPTION WHEN duplicate_object THEN null; "
                "END $$;"
            )
        )
        await conn.run_sync(Base.metadata.create_all)
    log_event(logger, logging.INFO, service="lending-service", operation="init_db", message="Database initialized")


async def serve():
    bootstrap("lending-service", metrics_port=METRICS_PORT, instrument_client=True)
    await init_db()

    server = grpc.aio.server(
        options=[
            ("grpc.max_send_message_length", 50 * 1024 * 1024),
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
        ]
    )

    lending_pb2_grpc.add_LendingServiceServicer_to_server(LendingServiceHandler(), server)

    listen_addr = f"{HOST}:{PORT}"
    server.add_insecure_port(listen_addr)
    await server.start()
    log_event(logger, logging.INFO, service="lending-service", operation="startup", message="Lending Service started", listen_addr=listen_addr)

    async def shutdown():
        log_event(logger, logging.INFO, service="lending-service", operation="shutdown", message="Shutting down Lending Service")
        await close_downstream_channels()
        await server.stop(5)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))

    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
