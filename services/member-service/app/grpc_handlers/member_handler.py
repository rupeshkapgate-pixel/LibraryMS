"""gRPC handlers for Member Service."""
import logging
import math

import grpc

from app.database import AsyncSessionLocal
from app.repositories.member_repository import MemberRepository
from app.models.member import MembershipStatus
from app.proto_generated import member_pb2, member_pb2_grpc, common_pb2

logger = logging.getLogger(__name__)


def _member_to_proto(member) -> member_pb2.Member:
    status = member_pb2.MembershipStatus.ACTIVE
    if member.membership_status == MembershipStatus.INACTIVE:
        status = member_pb2.MembershipStatus.INACTIVE

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


class MemberServiceHandler(member_pb2_grpc.MemberServiceServicer):

    async def CreateMember(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                repo = MemberRepository(session)
                existing = await repo.get_by_email(request.email)
                if existing:
                    context.set_code(grpc.StatusCode.ALREADY_EXISTS)
                    context.set_details(f"Member with email {request.email} already exists")
                    return member_pb2.Member()

                data = {
                    "full_name": request.full_name,
                    "email": request.email,
                    "phone": request.phone or None,
                    "address": request.address or None,
                }
                member = await repo.create(data)
                logger.info(f"Member created: {member.id}")
                return _member_to_proto(member)
        except Exception as exc:
            logger.error(f"CreateMember error: {exc}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return member_pb2.Member()

    async def UpdateMember(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                repo = MemberRepository(session)
                data = {}
                if request.full_name:
                    data["full_name"] = request.full_name
                if request.email:
                    data["email"] = request.email
                if request.phone:
                    data["phone"] = request.phone
                if request.address:
                    data["address"] = request.address

                member = await repo.update(request.id, data)
                if not member:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Member {request.id} not found")
                    return member_pb2.Member()
                return _member_to_proto(member)
        except Exception as exc:
            logger.error(f"UpdateMember error: {exc}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return member_pb2.Member()

    async def GetMember(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                repo = MemberRepository(session)
                member = await repo.get_by_id(request.id)
                if not member:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Member {request.id} not found")
                    return member_pb2.Member()
                return _member_to_proto(member)
        except Exception as exc:
            logger.error(f"GetMember error: {exc}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return member_pb2.Member()

    async def ListMembers(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                repo = MemberRepository(session)
                page = request.pagination.page or 1
                page_size = request.pagination.page_size or 20

                status = None
                if request.filter_by_status:
                    status = (
                        MembershipStatus.ACTIVE
                        if request.status == member_pb2.MembershipStatus.ACTIVE
                        else MembershipStatus.INACTIVE
                    )

                members, total = await repo.list_members(
                    page=page,
                    page_size=page_size,
                    status=status,
                    sort_by=request.sort_by or "created_at",
                    sort_order=request.sort_order or "desc",
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
            logger.error(f"ListMembers error: {exc}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return member_pb2.ListMembersResponse()

    async def ValidateActiveMember(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                repo = MemberRepository(session)
                member = await repo.get_by_id(request.member_id)
                if not member:
                    return member_pb2.ValidateActiveMemberResponse(
                        is_active=False,
                        message=f"Member {request.member_id} not found",
                    )
                if member.membership_status == MembershipStatus.INACTIVE:
                    return member_pb2.ValidateActiveMemberResponse(
                        is_active=False,
                        message="Member is inactive",
                        member=_member_to_proto(member),
                    )
                return member_pb2.ValidateActiveMemberResponse(
                    is_active=True,
                    message="Member is active",
                    member=_member_to_proto(member),
                )
        except Exception as exc:
            logger.error(f"ValidateActiveMember error: {exc}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return member_pb2.ValidateActiveMemberResponse()

    async def DeactivateMember(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                repo = MemberRepository(session)
                member = await repo.deactivate(request.id)
                if not member:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Member {request.id} not found")
                    return member_pb2.Member()
                return _member_to_proto(member)
        except Exception as exc:
            logger.error(f"DeactivateMember error: {exc}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return member_pb2.Member()
