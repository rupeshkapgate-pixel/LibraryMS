FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY services/api-gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/api-gateway/ .

COPY proto /proto
COPY scripts/fix_proto_imports.py /fix_proto_imports.py

RUN mkdir -p app/grpc_clients/proto_generated && \
    touch app/grpc_clients/proto_generated/__init__.py && \
    python -m grpc_tools.protoc -I /proto --python_out=app/grpc_clients/proto_generated --grpc_python_out=app/grpc_clients/proto_generated /proto/common.proto && \
    python -m grpc_tools.protoc -I /proto --python_out=app/grpc_clients/proto_generated --grpc_python_out=app/grpc_clients/proto_generated /proto/book.proto && \
    python -m grpc_tools.protoc -I /proto --python_out=app/grpc_clients/proto_generated --grpc_python_out=app/grpc_clients/proto_generated /proto/member.proto && \
    python -m grpc_tools.protoc -I /proto --python_out=app/grpc_clients/proto_generated --grpc_python_out=app/grpc_clients/proto_generated /proto/lending.proto && \
    python /fix_proto_imports.py app/grpc_clients/proto_generated

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
