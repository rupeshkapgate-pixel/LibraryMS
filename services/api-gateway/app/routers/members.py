"""Members router for API Gateway."""
from __future__ import annotations

import logging
from typing import Optional

import grpc
from fastapi import APIRouter, HTTPException, Query, Request, status

from app.grpc_clients import GRPC_TIMEOUT, get_member_channel
from app.grpc_clients.proto_generated import common_pb2, member_pb2, member_pb2_grpc
from app.schemas import MemberCreate, MemberResponse, MemberUpdate, PaginatedResponse, PaginationMeta
from app.telemetry.setup import make_grpc_metadata_with_trace

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/members", tags=["Members"])

STATUS_MAP = {
    grpc.StatusCode.NOT_FOUND: (404, "Not Found"),
    grpc.StatusCode.ALREADY_EXISTS: (409, "Already Exists"),
    grpc.StatusCode.FAILED_PRECONDITION: (400, "Bad Request"),
    grpc.StatusCode.INVALID_ARGUMENT: (422, "Validation Error"),
    grpc.StatusCode.UNAVAILABLE: (503, "Service Unavailable"),
}
STATUS_TEXT = {0: "ACTIVE", 1: "INACTIVE"}
STATUS_ENUM = {"ACTIVE": member_pb2.MembershipStatus.ACTIVE, "INACTIVE": member_pb2.MembershipStatus.INACTIVE}


def grpc_metadata(request: Request) -> list[tuple[str, str]]:
    correlation_id = getattr(request.state, "correlation_id", "-")
    base = [("x-correlation-id", correlation_id)] if correlation_id and correlation_id != "-" else []
    return make_grpc_metadata_with_trace(base)


def grpc_error_to_http(e: grpc.RpcError):
    code, default_msg = STATUS_MAP.get(e.code(), (500, "Internal Server Error"))
    logger.error(
        "Downstream gRPC call failed",
        extra={
            "grpc_code": e.code().name if e.code() else "UNKNOWN",
            "grpc_details": e.details(),
            "http_status": code,
        },
    )
    raise HTTPException(status_code=code, detail=e.details() or default_msg)


def _proto_to_member(m) -> MemberResponse:
    return MemberResponse(
        id=m.id,
        full_name=m.full_name,
        email=m.email,
        phone=m.phone or None,
        address=m.address or None,
        membership_status=STATUS_TEXT.get(m.membership_status, "ACTIVE"),
        created_at=m.created_at or None,
        updated_at=m.updated_at or None,
    )


@router.post("", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def create_member(body: MemberCreate, request: Request):
    try:
        stub = member_pb2_grpc.MemberServiceStub(get_member_channel())
        resp = await stub.CreateMember(
            member_pb2.CreateMemberRequest(
                full_name=body.full_name,
                email=body.email,
                phone=body.phone or "",
                address=body.address or "",
            ),
            timeout=GRPC_TIMEOUT,
            metadata=grpc_metadata(request),
        )
        return _proto_to_member(resp)
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.get("", response_model=PaginatedResponse[MemberResponse])
async def list_members(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: Optional[str] = Query(None, description="Search name, email, phone or address"),
    membership_status: Optional[str] = Query(None, pattern="^(ACTIVE|INACTIVE)$"),
    sort_by: str = "created_at",
    sort_order: str = "desc",
):
    try:
        stub = member_pb2_grpc.MemberServiceStub(get_member_channel())
        resp = await stub.ListMembers(
            member_pb2.ListMembersRequest(
                pagination=common_pb2.PaginationRequest(page=page, page_size=page_size),
                status=STATUS_ENUM.get(membership_status or "ACTIVE", member_pb2.MembershipStatus.ACTIVE),
                filter_by_status=membership_status is not None,
                sort_by=sort_by,
                sort_order=sort_order,
                query=q or "",
            ),
            timeout=GRPC_TIMEOUT,
            metadata=grpc_metadata(request),
        )
        return PaginatedResponse(
            data=[_proto_to_member(m) for m in resp.members],
            pagination=PaginationMeta(
                page=resp.pagination.page,
                page_size=resp.pagination.page_size,
                total_count=resp.pagination.total_count,
                total_pages=resp.pagination.total_pages,
            ),
        )
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.get("/{member_id}", response_model=MemberResponse)
async def get_member(member_id: str, request: Request):
    try:
        stub = member_pb2_grpc.MemberServiceStub(get_member_channel())
        resp = await stub.GetMember(
            member_pb2.GetMemberRequest(id=member_id),
            timeout=GRPC_TIMEOUT,
            metadata=grpc_metadata(request),
        )
        return _proto_to_member(resp)
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.put("/{member_id}", response_model=MemberResponse)
async def update_member(member_id: str, body: MemberUpdate, request: Request):
    try:
        stub = member_pb2_grpc.MemberServiceStub(get_member_channel())
        resp = await stub.UpdateMember(
            member_pb2.UpdateMemberRequest(
                id=member_id,
                full_name=body.full_name or "",
                email=body.email or "",
                phone=body.phone or "",
                address=body.address or "",
            ),
            timeout=GRPC_TIMEOUT,
            metadata=grpc_metadata(request),
        )
        return _proto_to_member(resp)
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_member(member_id: str, request: Request):
    try:
        stub = member_pb2_grpc.MemberServiceStub(get_member_channel())
        await stub.DeactivateMember(
            member_pb2.DeactivateMemberRequest(id=member_id),
            timeout=GRPC_TIMEOUT,
            metadata=grpc_metadata(request),
        )
    except grpc.RpcError as e:
        grpc_error_to_http(e)
