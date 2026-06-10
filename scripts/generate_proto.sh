#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
PROTO_DIR="$ROOT_DIR/proto"

SERVICES=(
  "services/api-gateway/app/grpc_clients"
  "services/book-service/app"
  "services/member-service/app"
  "services/lending-service/app"
)

echo "Generating protobuf files..."

for SERVICE in "${SERVICES[@]}"; do
  OUT_DIR="$ROOT_DIR/$SERVICE/proto_generated"
  mkdir -p "$OUT_DIR"
  touch "$OUT_DIR/__init__.py"

  python -m grpc_tools.protoc \
    -I "$PROTO_DIR" \
    --python_out="$OUT_DIR" \
    --grpc_python_out="$OUT_DIR" \
    "$PROTO_DIR/common.proto" \
    "$PROTO_DIR/book.proto" \
    "$PROTO_DIR/member.proto" \
    "$PROTO_DIR/lending.proto"

  echo "Generated for: $SERVICE"
done

echo "Done! Proto files generated."
