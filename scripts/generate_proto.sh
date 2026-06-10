#!/usr/bin/env bash
# Generate protobuf Python stubs for all services and fix relative imports.
# Usage: bash scripts/generate_proto.sh
#        make proto
#
# Requirements: pip install grpcio-tools protobuf
# Windows users: run from Git Bash or WSL, or use:
#   python -m grpc_tools.protoc ... directly (see README).
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
PROTO_DIR="$ROOT_DIR/proto"
FIX_SCRIPT="$SCRIPT_DIR/fix_proto_imports.py"

# Service -> output directory mapping
declare -A SERVICES=(
  ["services/book-service/app"]="proto_generated"
  ["services/member-service/app"]="proto_generated"
  ["services/lending-service/app"]="proto_generated"
  ["services/api-gateway/app/grpc_clients"]="proto_generated"
)

echo "Generating protobuf stubs..."
echo ""

for SVC_PATH in "${!SERVICES[@]}"; do
  OUT_DIR="$ROOT_DIR/$SVC_PATH/${SERVICES[$SVC_PATH]}"
  mkdir -p "$OUT_DIR"
  touch "$OUT_DIR/__init__.py"

  # Compile each proto file individually (easier to debug)
  for PROTO in common book member lending; do
    python -m grpc_tools.protoc \
      -I "$PROTO_DIR" \
      --python_out="$OUT_DIR" \
      --grpc_python_out="$OUT_DIR" \
      "$PROTO_DIR/${PROTO}.proto"
  done

  # Fix bare imports → relative imports
  python "$FIX_SCRIPT" "$OUT_DIR"
  echo "  ✓ $SVC_PATH"
done

echo ""
echo "Proto generation complete."
