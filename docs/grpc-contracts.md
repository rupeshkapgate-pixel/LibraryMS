# gRPC Contracts

## Proto files

```
proto/
├── common.proto    — PaginationRequest/Response, StatusResponse
├── book.proto      — Book messages + BookService RPCs
├── member.proto    — Member messages + MemberService RPCs
└── lending.proto   — LendingRecord + LendingService RPCs
```

## Generating stubs

```bash
make proto
# or
bash scripts/generate_proto.sh
```

Stubs are generated into:
- `services/book-service/app/proto_generated/`
- `services/member-service/app/proto_generated/`
- `services/lending-service/app/proto_generated/`
- `services/api-gateway/app/grpc_clients/proto_generated/`

After generation, `scripts/fix_proto_imports.py` rewrites bare imports
(`import common_pb2`) to relative imports (`from . import common_pb2`).

## Service RPCs

### BookService (:50051)

| RPC | Request | Response |
|-----|---------|----------|
| CreateBook | CreateBookRequest | Book |
| UpdateBook | UpdateBookRequest | Book |
| GetBook | GetBookRequest | Book |
| ListBooks | ListBooksRequest | ListBooksResponse |
| SearchBooks | SearchBooksRequest | SearchBooksResponse |
| CheckAvailability | CheckAvailabilityRequest | CheckAvailabilityResponse |
| DecreaseAvailableCopies | UpdateCopiesRequest | UpdateCopiesResponse |
| IncreaseAvailableCopies | UpdateCopiesRequest | UpdateCopiesResponse |
| DeleteBook | DeleteBookRequest | StatusResponse |

### MemberService (:50052)

| RPC | Request | Response |
|-----|---------|----------|
| CreateMember | CreateMemberRequest | Member |
| UpdateMember | UpdateMemberRequest | Member |
| GetMember | GetMemberRequest | Member |
| ListMembers | ListMembersRequest | ListMembersResponse |
| ValidateActiveMember | ValidateActiveMemberRequest | ValidateActiveMemberResponse |
| DeactivateMember | DeactivateMemberRequest | Member |

### LendingService (:50053)

| RPC | Request | Response |
|-----|---------|----------|
| BorrowBook | BorrowBookRequest | LendingRecord |
| ReturnBook | ReturnBookRequest | ReturnBookResponse |
| ListBorrowedBooks | ListBorrowedBooksRequest | ListBorrowedBooksResponse |
| ListBorrowedBooksByMember | ListBorrowedBooksByMemberRequest | ListBorrowedBooksResponse |
| ListBookBorrowHistory | ListBookBorrowHistoryRequest | ListBorrowedBooksResponse |
| ListOverdueBooks | ListOverdueBooksRequest | ListBorrowedBooksResponse |

## Health Checking

All three gRPC services implement the standard gRPC Health Checking Protocol
(`grpc.health.v1.Health`). Check with `grpc_health_probe`:

```bash
grpc_health_probe -addr=:50051 -service=book.BookService
grpc_health_probe -addr=:50052 -service=member.MemberService
grpc_health_probe -addr=:50053 -service=lending.LendingService
```
