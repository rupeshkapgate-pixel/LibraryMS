# Observability Guide

This project includes a Docker Compose observability stack:

| Tool | URL | Purpose |
|------|-----|---------|
| Prometheus | http://localhost:9090 | Metrics scraping and PromQL queries |
| Grafana | http://localhost:3001 | Dashboards for metrics/logs/traces. Login: `admin` / `admin` |
| Loki | http://localhost:3100 | Centralized log storage |
| Promtail | n/a | Docker log collector that ships logs to Loki |
| Jaeger | http://localhost:16686 | Distributed trace viewer |

## Structured JSON Logs

All backend services log in JSON format:

```json
{
  "timestamp": "2026-06-11T10:00:00+00:00",
  "level": "ERROR",
  "service": "book-service",
  "operation": "CreateBook",
  "correlation_id": "abc123",
  "message": "CreateBook failed",
  "error": "A transaction is already begun on this Session."
}
```

The API Gateway generates an `X-Correlation-ID` when the client does not provide one. That ID is logged by the API Gateway and forwarded to downstream gRPC services as metadata.

## How to Debug a Failed Request

1. Copy the `X-Correlation-ID` response header from the failed API call.
2. Open Grafana: http://localhost:3001
3. Go to **Explore** → select **Loki**.
4. Query by correlation ID:

```logql
{compose_project=~".*"} | json | correlation_id="<your-correlation-id>"
```

Or show errors:

```logql
{compose_project=~".*"} | json | level="ERROR"
```

## Metrics

Prometheus scrapes:

- API Gateway: `api-gateway:8000/metrics`
- Book Service: `book-service:9101/metrics`
- Member Service: `member-service:9102/metrics`
- Lending Service: `lending-service:9103/metrics`

Useful PromQL examples:

```promql
up
```

```promql
sum(rate(http_requests_total[5m])) by (handler, status)
```

```promql
db_queries_total
```

## Tracing

Jaeger is available at http://localhost:16686.
The backend services are configured to export OTLP spans to `jaeger:4317`.
