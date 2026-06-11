FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app:/app/app:/app/app/proto_generated

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    sed \
    && rm -rf /var/lib/apt/lists/*

COPY services/member-service/requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir --force-reinstall \
        protobuf==5.29.5 \
        grpcio==1.71.0 \
        grpcio-tools==1.71.0

COPY services/member-service/ .

COPY proto /proto

RUN mkdir -p app/proto_generated && \
    touch app/proto_generated/__init__.py && \
    python -m grpc_tools.protoc \
        -I /proto \
        --python_out=app/proto_generated \
        --grpc_python_out=app/proto_generated \
        /proto/common.proto /proto/book.proto /proto/member.proto /proto/lending.proto && \
    sed -i 's/^import common_pb2 as/from . import common_pb2 as/g' app/proto_generated/*_pb2.py && \
    sed -i 's/^import book_pb2 as/from . import book_pb2 as/g' app/proto_generated/*_pb2_grpc.py && \
    sed -i 's/^import member_pb2 as/from . import member_pb2 as/g' app/proto_generated/*_pb2_grpc.py && \
    sed -i 's/^import lending_pb2 as/from . import lending_pb2 as/g' app/proto_generated/*_pb2_grpc.py

EXPOSE 50052

CMD ["python", "main.py"]