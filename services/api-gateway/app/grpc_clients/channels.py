"""gRPC client factories for API Gateway."""
import os
import grpc

BOOK_SERVICE_HOST = os.getenv("BOOK_SERVICE_HOST", "localhost")
BOOK_SERVICE_PORT = os.getenv("BOOK_SERVICE_PORT", "50051")
MEMBER_SERVICE_HOST = os.getenv("MEMBER_SERVICE_HOST", "localhost")
MEMBER_SERVICE_PORT = os.getenv("MEMBER_SERVICE_PORT", "50052")
LENDING_SERVICE_HOST = os.getenv("LENDING_SERVICE_HOST", "localhost")
LENDING_SERVICE_PORT = os.getenv("LENDING_SERVICE_PORT", "50053")

GRPC_TIMEOUT = int(os.getenv("GRPC_TIMEOUT", "30"))

_CHANNEL_OPTIONS = [
    ("grpc.max_send_message_length", 50 * 1024 * 1024),
    ("grpc.max_receive_message_length", 50 * 1024 * 1024),
    ("grpc.keepalive_time_ms", 10000),
    ("grpc.keepalive_timeout_ms", 5000),
]


def get_book_channel():
    return grpc.aio.insecure_channel(
        f"{BOOK_SERVICE_HOST}:{BOOK_SERVICE_PORT}",
        options=_CHANNEL_OPTIONS,
    )


def get_member_channel():
    return grpc.aio.insecure_channel(
        f"{MEMBER_SERVICE_HOST}:{MEMBER_SERVICE_PORT}",
        options=_CHANNEL_OPTIONS,
    )


def get_lending_channel():
    return grpc.aio.insecure_channel(
        f"{LENDING_SERVICE_HOST}:{LENDING_SERVICE_PORT}",
        options=_CHANNEL_OPTIONS,
    )
