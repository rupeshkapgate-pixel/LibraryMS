"""API Gateway - FastAPI Application."""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.grpc_clients import GRPC_TIMEOUT, close_channels, get_book_channel, get_lending_channel, get_member_channel
from app.grpc_clients.proto_generated import book_pb2_grpc, common_pb2, lending_pb2_grpc, member_pb2_grpc
from app.middleware import CorrelationIdMiddleware
from app.observability.logging import configure_json_logging, log_event
from app.routers import books_router, lending_router, members_router
from app.schemas import DashboardStats, HealthResponse
from app.telemetry.setup import instrument_fastapi, instrument_grpc_client, make_grpc_metadata_with_trace, setup_tracing

configure_json_logging("api-gateway")
setup_tracing("api-gateway")
instrument_grpc_client()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Library Management System - API Gateway",
    description="REST API Gateway for Library Management System microservices",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://192.168.1.92:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CorrelationIdMiddleware)

app.include_router(books_router)
app.include_router(members_router)
app.include_router(lending_router)
instrument_fastapi(app)


@app.on_event("shutdown")
async def shutdown_grpc_channels() -> None:
    await close_channels()


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    services = {}

    async def check(name, channel_fn):
        try:
            await channel_fn().channel_ready()
            services[name] = "healthy"
        except Exception as exc:
            services[name] = "unhealthy"
            log_event(
                logger,
                logging.WARNING,
                service="api-gateway",
                operation="health_check",
                message=f"{name} health check failed",
                error=exc,
            )

    await check("book_service", get_book_channel)
    await check("member_service", get_member_channel)
    await check("lending_service", get_lending_channel)

    all_healthy = all(v == "healthy" for v in services.values())
    return HealthResponse(status="healthy" if all_healthy else "degraded", services=services)


@app.get("/api/v1/dashboard", response_model=DashboardStats, tags=["Dashboard"])
async def dashboard_stats():
    from app.grpc_clients.proto_generated import book_pb2, lending_pb2, member_pb2

    total_books = 0
    total_members = 0
    books_borrowed = 0
    overdue_books = 0

    try:
        book_stub = book_pb2_grpc.BookServiceStub(get_book_channel())
        resp = await book_stub.ListBooks(
            book_pb2.ListBooksRequest(pagination=common_pb2.PaginationRequest(page=1, page_size=1)),
            timeout=GRPC_TIMEOUT,
            metadata=make_grpc_metadata_with_trace(),
        )
        total_books = resp.pagination.total_count
    except Exception:
        logger.exception("Unable to read dashboard book stats")

    try:
        member_stub = member_pb2_grpc.MemberServiceStub(get_member_channel())
        resp = await member_stub.ListMembers(
            member_pb2.ListMembersRequest(pagination=common_pb2.PaginationRequest(page=1, page_size=1)),
            timeout=GRPC_TIMEOUT,
            metadata=make_grpc_metadata_with_trace(),
        )
        total_members = resp.pagination.total_count
    except Exception:
        logger.exception("Unable to read dashboard member stats")

    try:
        lending_stub = lending_pb2_grpc.LendingServiceStub(get_lending_channel())
        borrowed_resp = await lending_stub.ListBorrowedBooks(
            lending_pb2.ListBorrowedBooksRequest(pagination=common_pb2.PaginationRequest(page=1, page_size=1)),
            timeout=GRPC_TIMEOUT,
            metadata=make_grpc_metadata_with_trace(),
        )
        books_borrowed = borrowed_resp.pagination.total_count

        overdue_resp = await lending_stub.ListOverdueBooks(
            lending_pb2.ListOverdueBooksRequest(pagination=common_pb2.PaginationRequest(page=1, page_size=1)),
            timeout=GRPC_TIMEOUT,
            metadata=make_grpc_metadata_with_trace(),
        )
        overdue_books = overdue_resp.pagination.total_count
    except Exception:
        logger.exception("Unable to read dashboard lending stats")

    return DashboardStats(
        total_books=total_books,
        total_members=total_members,
        books_borrowed=books_borrowed,
        overdue_books=overdue_books,
    )
