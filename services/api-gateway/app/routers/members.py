"""Members router for API Gateway."""
import logging

import grpc
from fastapi import APIRouter, HTTPException, Query, status

from app.grpc_clients import get_member_channel, GRPC_TIMEOUT
from app.schemas import MemberCreate, MemberUpdate, MemberResponse, PaginatedResponse, PaginationMeta
from app.grpc_clients.proto_generated import member_pb2, member_pb2_grpc, common_pb2

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/members", tags=["Members"])

STATUS_MAP = {
    grpc.StatusCode.NOT_FOUND: (404, "Not Found"),
    grpc.StatusCode.ALREADY_EXISTS: (409, "Already Exists"),
    grpc.StatusCode.FAILED_PRECONDITION: (400, "Bad Request"),
}

STATUS_TEXT = {0: "ACTIVE", 1: "INACTIVE"}


def grpc_error_to_http(e: grpc.RpcError):
    code, default_msg = STATUS_MAP.get(e.code(), (500, "Internal Server Error"))
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
async def create_member(body: MemberCreate):
    try:
        async with get_member_channel() as channel:
            stub = member_pb2_grpc.MemberServiceStub(channel)
            resp = await stub.CreateMember(
                member_pb2.CreateMemberRequest(
                    full_name=body.full_name,
                    email=body.email,
                    phone=body.phone or "",
                    address=body.address or "",
                ),
                timeout=GRPC_TIMEOUT,
            )
            return _proto_to_member(resp)
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.get("", response_model=PaginatedResponse[MemberResponse])
async def list_members(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = "created_at",
    sort_order: str = "desc",
):
    try:
        async with get_member_channel() as channel:
            stub = member_pb2_grpc.MemberServiceStub(channel)
            resp = await stub.ListMembers(
                member_pb2.ListMembersRequest(
                    pagination=common_pb2.PaginationRequest(page=page, page_size=page_size),
                    sort_by=sort_by,
                    sort_order=sort_order,
                ),
                timeout=GRPC_TIMEOUT,
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
async def get_member(member_id: str):
    try:
        async with get_member_channel() as channel:
            stub = member_pb2_grpc.MemberServiceStub(channel)
            resp = await stub.GetMember(
                member_pb2.GetMemberRequest(id=member_id),
                timeout=GRPC_TIMEOUT,
            )
            return _proto_to_member(resp)
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.put("/{member_id}", response_model=MemberResponse)
async def update_member(member_id: str, body: MemberUpdate):
    try:
        async with get_member_channel() as channel:
            stub = member_pb2_grpc.MemberServiceStub(channel)
            resp = await stub.UpdateMember(
                member_pb2.UpdateMemberRequest(
                    id=member_id,
                    full_name=body.full_name or "",
                    email=body.email or "",
                    phone=body.phone or "",
                    address=body.address or "",
                ),
                timeout=GRPC_TIMEOUT,
            )
            return _proto_to_member(resp)
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_member(member_id: str):
    try:
        async with get_member_channel() as channel:
            stub = member_pb2_grpc.MemberServiceStub(channel)
            await stub.DeactivateMember(
                member_pb2.DeactivateMemberRequest(id=member_id),
                timeout=GRPC_TIMEOUT,
            )
    except grpc.RpcError as e:
        grpc_error_to_http(e)
