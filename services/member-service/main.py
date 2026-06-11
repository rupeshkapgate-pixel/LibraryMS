"""Member Service gRPC Server."""
import asyncio
import logging
import os
import signal

import grpc

from app.grpc_handlers.member_handler import MemberServiceHandler
from app.proto_generated import member_pb2_grpc
from app.database import engine
from app.models.member import Base

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

HOST = os.getenv("GRPC_HOST", "0.0.0.0")
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
    logger.info("Database initialized")


async def serve():
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
    logger.info(f"Member Service started on {listen_addr}")

    async def shutdown():
        logger.info("Shutting down Member Service...")
        await server.stop(5)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))

    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
