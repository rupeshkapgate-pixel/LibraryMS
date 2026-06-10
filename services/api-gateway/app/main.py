"""API Gateway — FastAPI Application."""
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.middleware import CorrelationIdMiddleware
from app.routers import books_router, members_router, lending_router
from app.grpc_clients import get_book_channel, get_member_channel, get_lending_channel, GRPC_TIMEOUT
from app.grpc_clients.proto_generated import (
    book_pb2, book_pb2_grpc,
    member_pb2, member_pb2_grpc,
    lending_pb2, lending_pb2_grpc,
    common_pb2,
)
from app.schemas import HealthResponse, DashboardStats

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Library Management System — API Gateway",
    description=(
        "REST facade over gRPC microservices for managing books, members, and lending.\n\n"
        "All errors return `{\"error\": \"CODE\", \"message\": \"...\", \"details\": {}}`."
    ),
    version="1.0.0",
    contact={"name": "Library Platform Team", "email": "platform@library.example.com"},
    license_info={"name": "MIT"},
)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-ID", "X-Process-Time"],
)
app.add_middleware(CorrelationIdMiddleware)

app.include_router(books_router)
app.include_router(members_router)
app.include_router(lending_router)


async def _ping(channel_fn) -> str:
    try:
        async with channel_fn() as ch:
            await ch.channel_ready()
        return "healthy"
    except Exception:
        return "unhealthy"


@app.get("/health", tags=["Observability"], summary="Deep health check")
async def health_check():
    services = {
        "book_service":    await _ping(get_book_channel),
        "member_service":  await _ping(get_member_channel),
        "lending_service": await _ping(get_lending_channel),
    }
    all_ok = all(v == "healthy" for v in services.values())
    payload = {"status": "healthy" if all_ok else "degraded", "services": services}
    return JSONResponse(content=payload, status_code=200 if all_ok else 503)


@app.get("/ready", tags=["Observability"], summary="Readiness probe")
async def readiness():
    """Kubernetes readiness probe — returns 200 when gateway can accept traffic."""
    return {"ready": True}


@app.get("/api/v1/dashboard", response_model=DashboardStats, tags=["Dashboard"])
async def dashboard_stats():
    total_books = total_members = books_borrowed = overdue_books = 0
    try:
        async with get_book_channel() as ch:
            r = await book_pb2_grpc.BookServiceStub(ch).ListBooks(
                book_pb2.ListBooksRequest(
                    pagination=common_pb2.PaginationRequest(page=1, page_size=1)
                ), timeout=GRPC_TIMEOUT,
            )
            total_books = r.pagination.total_count
    except Exception:
        pass
    try:
        async with get_member_channel() as ch:
            r = await member_pb2_grpc.MemberServiceStub(ch).ListMembers(
                member_pb2.ListMembersRequest(
                    pagination=common_pb2.PaginationRequest(page=1, page_size=1)
                ), timeout=GRPC_TIMEOUT,
            )
            total_members = r.pagination.total_count
    except Exception:
        pass
    try:
        async with get_lending_channel() as ch:
            stub = lending_pb2_grpc.LendingServiceStub(ch)
            br = await stub.ListBorrowedBooks(
                lending_pb2.ListBorrowedBooksRequest(
                    pagination=common_pb2.PaginationRequest(page=1, page_size=1)
                ), timeout=GRPC_TIMEOUT,
            )
            books_borrowed = br.pagination.total_count
            od = await stub.ListOverdueBooks(
                lending_pb2.ListOverdueBooksRequest(
                    pagination=common_pb2.PaginationRequest(page=1, page_size=1)
                ), timeout=GRPC_TIMEOUT,
            )
            overdue_books = od.pagination.total_count
    except Exception:
        pass
    return DashboardStats(
        total_books=total_books, total_members=total_members,
        books_borrowed=books_borrowed, overdue_books=overdue_books,
    )
