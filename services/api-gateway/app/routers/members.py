"""Members router — REST ↔ gRPC with standardised error responses."""
from __future__ import annotations
import logging
import grpc
from fastapi import APIRouter, HTTPException, Query, status
from app.grpc_clients import get_member_channel, GRPC_TIMEOUT
from app.grpc_clients.proto_generated import member_pb2, member_pb2_grpc, common_pb2
from app.schemas import MemberCreate, MemberUpdate, MemberResponse, PaginatedResponse, PaginationMeta

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/members", tags=["Members"])

_GRPC_STATUS_MAP = {
    grpc.StatusCode.NOT_FOUND:           (404, "NOT_FOUND"),
    grpc.StatusCode.ALREADY_EXISTS:      (409, "ALREADY_EXISTS"),
    grpc.StatusCode.FAILED_PRECONDITION: (409, "PRECONDITION_FAILED"),
    grpc.StatusCode.UNAVAILABLE:         (503, "SERVICE_UNAVAILABLE"),
    grpc.StatusCode.INTERNAL:            (500, "INTERNAL_ERROR"),
}
_STATUS_TEXT = {0: "ACTIVE", 1: "INACTIVE"}


def grpc_error_to_http(e: grpc.RpcError) -> None:
    http_status, error_code = _GRPC_STATUS_MAP.get(e.code(), (500, "INTERNAL_ERROR"))
    raise HTTPException(
        status_code=http_status,
        detail={"error": error_code, "message": e.details() or e.code().name, "details": {}},
    )


def _to_response(m) -> MemberResponse:
    return MemberResponse(
        id=m.id, full_name=m.full_name, email=m.email,
        phone=m.phone or None, address=m.address or None,
        membership_status=_STATUS_TEXT.get(m.membership_status, "ACTIVE"),
        created_at=m.created_at or None, updated_at=m.updated_at or None,
    )

def _pag(p) -> PaginationMeta:
    return PaginationMeta(page=p.page, page_size=p.page_size, total_count=p.total_count, total_pages=p.total_pages)


@router.post("", response_model=MemberResponse, status_code=status.HTTP_201_CREATED,
             summary="Register a new member",
             responses={409: {"description": "Email already registered"}})
async def create_member(body: MemberCreate):
    try:
        async with get_member_channel() as ch:
            resp = await member_pb2_grpc.MemberServiceStub(ch).CreateMember(
                member_pb2.CreateMemberRequest(
                    full_name=body.full_name, email=body.email,
                    phone=body.phone or "", address=body.address or "",
                ),
                timeout=GRPC_TIMEOUT,
            )
        return _to_response(resp)
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.get("", response_model=PaginatedResponse[MemberResponse], summary="List members")
async def list_members(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = "created_at",
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
):
    try:
        async with get_member_channel() as ch:
            resp = await member_pb2_grpc.MemberServiceStub(ch).ListMembers(
                member_pb2.ListMembersRequest(
                    pagination=common_pb2.PaginationRequest(page=page, page_size=page_size),
                    sort_by=sort_by, sort_order=sort_order,
                ),
                timeout=GRPC_TIMEOUT,
            )
        return PaginatedResponse(data=[_to_response(m) for m in resp.members], pagination=_pag(resp.pagination))
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.get("/{member_id}", response_model=MemberResponse, summary="Get member by ID")
async def get_member(member_id: str):
    try:
        async with get_member_channel() as ch:
            resp = await member_pb2_grpc.MemberServiceStub(ch).GetMember(
                member_pb2.GetMemberRequest(id=member_id), timeout=GRPC_TIMEOUT,
            )
        return _to_response(resp)
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.put("/{member_id}", response_model=MemberResponse, summary="Update member details")
async def update_member(member_id: str, body: MemberUpdate):
    try:
        async with get_member_channel() as ch:
            resp = await member_pb2_grpc.MemberServiceStub(ch).UpdateMember(
                member_pb2.UpdateMemberRequest(
                    id=member_id, full_name=body.full_name or "",
                    email=body.email or "", phone=body.phone or "", address=body.address or "",
                ),
                timeout=GRPC_TIMEOUT,
            )
        return _to_response(resp)
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Deactivate a member")
async def deactivate_member(member_id: str):
    try:
        async with get_member_channel() as ch:
            await member_pb2_grpc.MemberServiceStub(ch).DeactivateMember(
                member_pb2.DeactivateMemberRequest(id=member_id), timeout=GRPC_TIMEOUT,
            )
    except grpc.RpcError as e:
        grpc_error_to_http(e)
