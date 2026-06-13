"""gRPC handlers for Member Service.

Handlers delegate business logic to MemberService and only translate protobuf and
gRPC status concerns.
"""
from __future__ import annotations

import logging
import math

import grpc
from sqlalchemy.exc import IntegrityError

from app.database import AsyncSessionLocal
from app.models.member import Member, MembershipStatus
from app.observability.logging import get_grpc_correlation_id, log_event
from app.proto_generated import common_pb2, member_pb2, member_pb2_grpc
from app.services.member_service import MemberService

logger = logging.getLogger(__name__)
_SERVICE = "member-service"


def _log_error(operation: str, context, exc: Exception) -> None:
    log_event(
        logger,
        logging.ERROR,
        service=_SERVICE,
        operation=operation,
        correlation_id=get_grpc_correlation_id(context),
        message=f"{operation} failed",
        error=exc,
    )


def _log_info(operation: str, context, message: str, **extra) -> None:
    log_event(
        logger,
        logging.INFO,
        service=_SERVICE,
        operation=operation,
        correlation_id=get_grpc_correlation_id(context),
        message=message,
        **extra,
    )


def _member_to_proto(member: Member) -> member_pb2.Member:
    status = member_pb2.MembershipStatus.INACTIVE if member.membership_status == MembershipStatus.INACTIVE else member_pb2.MembershipStatus.ACTIVE
    return member_pb2.Member(
        id=str(member.id),
        full_name=member.full_name or "",
        email=member.email or "",
        phone=member.phone or "",
        address=member.address or "",
        membership_status=status,
        created_at=member.created_at.isoformat() if member.created_at else "",
        updated_at=member.updated_at.isoformat() if member.updated_at else "",
        deleted_at=member.deleted_at.isoformat() if member.deleted_at else "",
    )


def _set_error(context, exc: Exception) -> None:
    if isinstance(exc, LookupError):
        context.set_code(grpc.StatusCode.NOT_FOUND)
    elif isinstance(exc, IntegrityError):
        context.set_code(grpc.StatusCode.ALREADY_EXISTS)
    elif isinstance(exc, ValueError):
        msg = str(exc).lower()
        context.set_code(grpc.StatusCode.ALREADY_EXISTS if "already exists" in msg else grpc.StatusCode.INVALID_ARGUMENT)
    else:
        context.set_code(grpc.StatusCode.INTERNAL)
    context.set_details(str(exc))


class MemberServiceHandler(member_pb2_grpc.MemberServiceServicer):
    async def CreateMember(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                service = MemberService(session)
                member = await service.create_member(
                    {
                        "full_name": request.full_name,
                        "email": request.email,
                        "phone": request.phone or None,
                        "address": request.address or None,
                    }
                )
                _log_info("CreateMember", context, "Member created", member_id=str(member.id), email=member.email)
                return _member_to_proto(member)
        except Exception as exc:
            _log_error("CreateMember", context, exc)
            _set_error(context, exc)
            return member_pb2.Member()

    async def UpdateMember(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                service = MemberService(session)
                data = {}
                if request.full_name:
                    data["full_name"] = request.full_name
                if request.email:
                    data["email"] = request.email
                if request.phone:
                    data["phone"] = request.phone
                if request.address:
                    data["address"] = request.address

                member = await service.update_member(request.id, data)
                if not member:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Member {request.id} not found")
                    return member_pb2.Member()
                return _member_to_proto(member)
        except Exception as exc:
            _log_error("UpdateMember", context, exc)
            _set_error(context, exc)
            return member_pb2.Member()

    async def GetMember(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                service = MemberService(session)
                member = await service.get_member(request.id)
                if not member:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Member {request.id} not found")
                    return member_pb2.Member()
                return _member_to_proto(member)
        except Exception as exc:
            _log_error("GetMember", context, exc)
            _set_error(context, exc)
            return member_pb2.Member()

    async def ListMembers(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                service = MemberService(session)
                page = request.pagination.page or 1
                page_size = request.pagination.page_size or 20
                status = None
                if request.filter_by_status:
                    status = MembershipStatus.ACTIVE if request.status == member_pb2.MembershipStatus.ACTIVE else MembershipStatus.INACTIVE

                members, total = await service.list_members(
                    page=page,
                    page_size=page_size,
                    status=status,
                    sort_by=request.sort_by or "created_at",
                    sort_order=request.sort_order or "desc",
                    query=request.query or None,
                )
                total_pages = math.ceil(total / page_size) if page_size > 0 else 0
                return member_pb2.ListMembersResponse(
                    members=[_member_to_proto(m) for m in members],
                    pagination=common_pb2.PaginationResponse(
                        page=page,
                        page_size=page_size,
                        total_count=total,
                        total_pages=total_pages,
                    ),
                )
        except Exception as exc:
            _log_error("ListMembers", context, exc)
            _set_error(context, exc)
            return member_pb2.ListMembersResponse()

    async def ValidateActiveMember(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                service = MemberService(session)
                is_active, message, member = await service.validate_active(request.member_id)
                response = member_pb2.ValidateActiveMemberResponse(is_active=is_active, message=message)
                if member:
                    response.member.CopyFrom(_member_to_proto(member))
                return response
        except Exception as exc:
            _log_error("ValidateActiveMember", context, exc)
            _set_error(context, exc)
            return member_pb2.ValidateActiveMemberResponse()

    async def DeactivateMember(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                service = MemberService(session)
                member = await service.deactivate(request.id)
                if not member:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Member {request.id} not found")
                    return member_pb2.Member()
                return _member_to_proto(member)
        except Exception as exc:
            _log_error("DeactivateMember", context, exc)
            _set_error(context, exc)
            return member_pb2.Member()
