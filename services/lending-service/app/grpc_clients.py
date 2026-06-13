"""Reusable downstream gRPC clients for Lending Service.

Borrow/return workflows call Book and Member services. Reusing process-scoped
channels avoids creating a new HTTP/2 connection for every gRPC request.
"""
from __future__ import annotations

import os
from typing import Dict

import grpc

from app.proto_generated import book_pb2_grpc, member_pb2_grpc

BOOK_SERVICE_ADDR = f"{os.getenv('BOOK_SERVICE_HOST', 'localhost')}:{os.getenv('BOOK_SERVICE_PORT', '50051')}"
MEMBER_SERVICE_ADDR = f"{os.getenv('MEMBER_SERVICE_HOST', 'localhost')}:{os.getenv('MEMBER_SERVICE_PORT', '50052')}"

# Keepalive pings are intentionally disabled here.
#
# The first shared-channel refactor used an aggressive 10s keepalive with
# ``grpc.keepalive_permit_without_calls=1``. gRPC servers treat frequent idle
# pings as abusive and close the HTTP/2 connection with GOAWAY /
# ENHANCE_YOUR_CALM / "too_many_pings", which caused fast 500 responses on
# routes such as POST /api/v1/books. Reusing channels is still correct; the
# fix is to let gRPC manage idle connections instead of pinging continuously.
_CHANNEL_OPTIONS = [
    ("grpc.max_send_message_length", 50 * 1024 * 1024),
    ("grpc.max_receive_message_length", 50 * 1024 * 1024),
]

_CHANNELS: Dict[str, grpc.aio.Channel] = {}


def _channel(name: str, target: str) -> grpc.aio.Channel:
    channel = _CHANNELS.get(name)
    if channel is None:
        channel = grpc.aio.insecure_channel(target, options=_CHANNEL_OPTIONS)
        _CHANNELS[name] = channel
    return channel


def get_book_channel() -> grpc.aio.Channel:
    return _channel("book", BOOK_SERVICE_ADDR)


def get_member_channel() -> grpc.aio.Channel:
    return _channel("member", MEMBER_SERVICE_ADDR)


def get_book_stub() -> book_pb2_grpc.BookServiceStub:
    return book_pb2_grpc.BookServiceStub(get_book_channel())


def get_member_stub() -> member_pb2_grpc.MemberServiceStub:
    return member_pb2_grpc.MemberServiceStub(get_member_channel())


async def close_downstream_channels() -> None:
    channels = list(_CHANNELS.values())
    _CHANNELS.clear()
    for channel in channels:
        await channel.close()
