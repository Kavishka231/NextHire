# Production observability and service objectives

NextHire exposes Prometheus metrics on the private backend `/metrics` endpoint.
Nginx does not proxy this endpoint publicly. The `observability` Compose profile
runs Prometheus and a provisioned Grafana dashboard:

```sh
GRAFANA_ADMIN_PASSWORD='use-a-secret-manager-value' docker compose --profile observability up -d
```

Grafana listens on loopback port 3000 by default. Access it through an SSH
tunnel or a separately authenticated operations proxy; do not expose it openly.

## Metrics

- HTTP request totals by method, normalized route, and status;
- request latency histogram and in-progress request count;
- PostgreSQL and Redis reachability;
- database pool size and checked-out connections;
- Celery default queue depth and cumulative task failures;
- application release/environment identity and process uptime; and
- standard Python process/runtime metrics from `prometheus_client`.

Route templates such as `/api/v1/jobs/{job_id}` are used instead of raw URLs,
preventing IDs or query strings from creating unbounded metric labels.
Dependency probes have one-second connection/read timeouts and update when
Prometheus scrapes the endpoint.

## Initial SLOs

These are initial targets for a small production service, not claims about
performance that has not yet been measured. Review them after 30 days of real
traffic and adjust only through a documented reliability review.

| Objective | Target | Measurement | Rationale |
| --- | --- | --- | --- |
| API availability | >= 99.5% over 30 days | Non-5xx API responses / all API responses | Allows about 3h 39m monthly unavailability, realistic for a small service without multi-region failover while still requiring disciplined operation. |
| API server error rate | < 1% over rolling 30 minutes | 5xx API responses / all API responses | Client validation failures are excluded; sustained server failures above 1% indicate a real regression or dependency incident. |
| API p95 latency | < 500 ms over rolling 30 minutes | Histogram p95 across API routes | Most requests are database-backed CRUD/search operations. 500 ms is user-visible but achievable before advanced caching or horizontal autoscaling. External job-provider latency should be reviewed separately. |

The availability and error objectives overlap intentionally: availability is a
monthly customer outcome, while the shorter error-rate window detects incidents
quickly. Low-traffic windows must use minimum-volume alert conditions so a
single request does not create a misleading percentage.

## Dashboard interpretation

The provisioned overview shows the three SLO indicators, request rate by status,
dependency state, uptime, database connection usage, queue depth, and Celery
failures. Dashboards support investigation; alerts and notification routing are
defined separately so operators do not have to watch a screen continuously.
