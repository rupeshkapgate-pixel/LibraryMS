# OpenTelemetry and Jaeger Validation

This backend package includes OpenTelemetry SDK setup, FastAPI instrumentation, gRPC aio client/server instrumentation, OTLP export to Jaeger, and explicit W3C TraceContext propagation in outgoing gRPC metadata.

## Run

```bash
docker compose down
docker compose build --no-cache api-gateway book-service member-service lending-service
docker compose up -d
```

## Validate Jaeger

Open:

```text
http://localhost:16686
```

Trigger requests:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/books
curl http://localhost:8000/api/v1/members
```

Expected services in Jaeger:

- api-gateway
- book-service
- member-service
- lending-service

Expected flow for REST -> gRPC:

```text
api-gateway HTTP span
  -> grpc client span
     -> downstream gRPC server span
```

## Validate Loki Logs

Grafana:

```text
http://localhost:3001
```

Use Explore -> Loki:

```logql
{service=~"api-gateway|book-service|member-service|lending-service"} | json
```

Search by correlation ID:

```logql
{service=~".+"} |= "<correlation-id>"
```

## Validate Prometheus

Open:

```text
http://localhost:9090/targets
```

Useful queries:

```promql
up
grpc_server_requests_total
db_queries_total
http_requests_total
```
