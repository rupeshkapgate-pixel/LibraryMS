FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY services/member-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/member-service/ .

COPY proto /proto
COPY scripts/fix_proto_imports.py /fix_proto_imports.py

RUN mkdir -p app/proto_generated && \
    touch app/proto_generated/__init__.py && \
    python -m grpc_tools.protoc -I /proto --python_out=app/proto_generated --grpc_python_out=app/proto_generated /proto/common.proto && \
    python -m grpc_tools.protoc -I /proto --python_out=app/proto_generated --grpc_python_out=app/proto_generated /proto/book.proto && \
    python -m grpc_tools.protoc -I /proto --python_out=app/proto_generated --grpc_python_out=app/proto_generated /proto/member.proto && \
    python -m grpc_tools.protoc -I /proto --python_out=app/proto_generated --grpc_python_out=app/proto_generated /proto/lending.proto && \
    python /fix_proto_imports.py app/proto_generated

EXPOSE 50052

CMD ["python", "main.py"]
