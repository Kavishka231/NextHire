# Production alerting

NextHire uses Prometheus rules and Alertmanager to turn observed failures into
operator notifications:

```text
Metric -> threshold and duration -> alert -> Alertmanager -> webhook receiver
```

## Alert policy

| Signal | Threshold | Severity | Reason |
| --- | --- | --- | --- |
| API scrape | unavailable for 2 minutes | Critical | The service or metrics path is unreachable. |
| API 5xx rate | above 5% for 10 minutes, with at least 20 requests | Critical | A sustained customer-facing failure needs immediate action. |
| API error-rate SLO | above 1% for 30 minutes, with at least 100 requests | Warning | Warns before an extended error-budget burn becomes an incident. |
| API p95 latency | above 500 ms for 15 minutes, with at least 20 requests | Warning | Matches the documented latency SLO without paging on a brief spike. |
| 30-day availability | below 99.5%, with at least 1,000 requests | Warning | Indicates the monthly objective is at risk. |
| PostgreSQL | unavailable for 1 minute | Critical | Most application workflows cannot function without the database. |
| Redis | unavailable for 2 minutes | Critical | Rate limiting, caching, and task delivery can be impaired. |
| Celery queue | more than 100 waiting tasks for 15 minutes | Warning | Detects sustained worker backlog rather than a normal burst. |
| Celery failures | any increase over 10 minutes | Warning | Failed background work requires investigation. |
| Host disk | above 80% for 10 minutes | Warning | Creates time to add capacity or remove safe data. |
| Host disk | above 90% for 5 minutes | Critical | An exhausted disk can corrupt or stop application services. |

Percentage alerts include minimum traffic volumes so one failed request on a
quiet service does not create a misleading page. These are initial thresholds;
review them against 30 days of production data and incident history.

## Configure notifications

Create `observability/secrets/alert-webhook-url` on the deployment host with one
HTTPS endpoint that accepts the Alertmanager generic webhook payload. Restrict
the file to the deployment account (`chmod 600`) and never commit it. To store
the secret elsewhere, set `ALERT_WEBHOOK_URL_FILE` to its absolute host path.

Start the stack with:

```bash
docker compose --profile observability up -d
```

Alertmanager groups related alerts, repeats critical notifications every 30
minutes, repeats warnings every four hours, sends resolved notifications, and
suppresses a warning when the equivalent critical alert is active.

## Verify before production

Run `promtool check config` and `promtool check rules` against the mounted
configuration in CI or staging. Send a controlled test alert to a non-production
receiver and confirm delivery and resolution. Quarterly, repeat the notification
test and simulate API, database, Redis, and disk failures in staging. Every alert
must have an owner and a documented response; remove alerts that cannot produce
an operator action.
