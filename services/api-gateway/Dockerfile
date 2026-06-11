# syntax=docker/dockerfile:1

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

# Install service dependencies first for cache efficiency.
COPY services/api-gateway/requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt \
    && python -m pip install --force-reinstall \
        protobuf==5.29.5 \
        grpcio==1.71.0 \
        grpcio-tools==1.71.0

# Copy API Gateway source.
COPY services/api-gateway/ ./

# Copy proto definitions and generate Python gRPC artifacts inside the image.
COPY proto /proto
RUN mkdir -p app/grpc_clients/proto_generated \
    && touch app/grpc_clients/proto_generated/__init__.py \
    && python -m grpc_tools.protoc \
        -I /proto \
        --python_out=app/grpc_clients/proto_generated \
        --grpc_python_out=app/grpc_clients/proto_generated \
        /proto/common.proto /proto/book.proto /proto/member.proto /proto/lending.proto

# Generated grpc files use absolute imports such as `import common_pb2`.
ENV PYTHONPATH=/app:/app/app/grpc_clients/proto_generated

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
