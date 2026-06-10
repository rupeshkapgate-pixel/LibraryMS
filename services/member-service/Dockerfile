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
RUN mkdir -p app/proto_generated && \
    touch app/proto_generated/__init__.py && \
    python -m grpc_tools.protoc \
        -I /proto \
        --python_out=app/proto_generated \
        --grpc_python_out=app/proto_generated \
        /proto/common.proto /proto/book.proto /proto/member.proto /proto/lending.proto

EXPOSE 50052

CMD ["python", "main.py"]
