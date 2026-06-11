"""Member Service gRPC Server."""
import asyncio
import logging
import os
import signal

import grpc

from app.grpc_handlers.member_handler import MemberServiceHandler
from app.proto_generated import member_pb2_grpc
from app.database import engine
from app.observability.logging import configure_json_logging, log_event
from app.telemetry.setup import bootstrap
from app.models.member import Base

configure_json_logging("member-service")
logger = logging.getLogger(__name__)

HOST = os.getenv("GRPC_HOST", "0.0.0.0")
METRICS_PORT = int(os.getenv("METRICS_PORT", "9102"))
PORT = int(os.getenv("GRPC_PORT", "50052"))


async def init_db():
    async with engine.begin() as conn:
        await conn.execute(
            __import__("sqlalchemy").text("CREATE SCHEMA IF NOT EXISTS members_db")
        )
        await conn.execute(
            __import__("sqlalchemy").text(
                "DO $$ BEGIN "
                "CREATE TYPE members_db.membershipstatus AS ENUM ('ACTIVE', 'INACTIVE'); "
                "EXCEPTION WHEN duplicate_object THEN null; "
                "END $$;"
            )
        )
        await conn.run_sync(Base.metadata.create_all)
    log_event(logger, logging.INFO, service="member-service", operation="init_db", message="Database initialized")


async def serve():
    bootstrap("member-service", metrics_port=METRICS_PORT)
    await init_db()

    server = grpc.aio.server(
        options=[
            ("grpc.max_send_message_length", 50 * 1024 * 1024),
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
        ]
    )

    member_pb2_grpc.add_MemberServiceServicer_to_server(MemberServiceHandler(), server)

    listen_addr = f"{HOST}:{PORT}"
    server.add_insecure_port(listen_addr)
    await server.start()
    log_event(logger, logging.INFO, service="member-service", operation="startup", message="Member Service started", listen_addr=listen_addr)

    async def shutdown():
        log_event(logger, logging.INFO, service="member-service", operation="shutdown", message="Shutting down Member Service")
        await server.stop(5)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))

    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
