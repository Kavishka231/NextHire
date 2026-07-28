# NextHire deployment

## Required configuration

Copy `.env.example` to `.env`, replace every `replace-*` value, and set:

- `ENVIRONMENT=production`
- a random `SECRET_KEY` containing at least 32 characters
- a strong `POSTGRES_PASSWORD`
- the public HTTPS `PUBLIC_APP_URL`
- the exact comma-separated HTTPS origins in `CORS_ORIGINS`
- SMTP and Adzuna credentials when those integrations are required

Password-reset links use `PUBLIC_APP_URL`, expire after
`RESET_TOKEN_EXPIRE_MINUTES`, and are delivered by the Celery worker. Verify
SMTP delivery and the public reset URL before opening registration.

Refresh sessions expire after `REFRESH_TOKEN_EXPIRE_DAYS`. Every refresh
rotates the refresh token, and the Celery scheduler removes expired or revoked
tokens daily at 03:00 UTC.
Refresh tokens are sent only in an HttpOnly, SameSite cookie. Set
`REFRESH_COOKIE_SECURE=true` in production; production startup rejects an
insecure refresh-cookie configuration.

Authentication and admin-email endpoints use Redis-backed rate limits. Tune
`AUTH_RATE_LIMIT_PER_MINUTE`, `REGISTER_RATE_LIMIT_PER_MINUTE`, and
`EMAIL_RATE_LIMIT_PER_HOUR` for expected production traffic. These endpoints
fail closed with HTTP 503 when Redis is unavailable.

All user-facing email is delivered by Celery. `MAIL_TIMEOUT_SECONDS` bounds
SMTP connection and read operations. Verify the sender address with the SMTP
provider before testing password resets, reminders, individual admin email, or
broadcasts.

Administrator bootstrap is off by default. To create the first administrator,
set `SEED_ADMIN=true` with `ADMIN_EMAIL` and a password of at least 12
characters, deploy once, then set `SEED_ADMIN=false` and redeploy.

## Release

```sh
docker compose config --quiet
docker compose build --pull
docker compose --profile operations run --rm migrate
docker compose up -d
docker compose ps
curl --fail http://localhost:5500/
curl --fail http://localhost:5500/api/v1/jobs
```

After deployment, confirm Alembic reports migration `009` as the current head.
Migration `009` intentionally expires refresh tokens created by earlier
versions, so existing users must sign in again after this release.

Migrations are a controlled release step and are not run automatically by API
container startup. Before running them, take or verify a database snapshot.
Stop the release if the migration command fails; do not start the new
application image against a partially migrated database.

Only the frontend port is published. PostgreSQL, Redis, the API, and the worker
remain on the private Compose network. Put the frontend behind a platform load
balancer or TLS reverse proxy and expose HTTPS only.

## HTTPS proxy

Terminate TLS at the production load balancer or reverse proxy using a
certificate for the real application domain. The proxy must:

- redirect public HTTP traffic to HTTPS;
- send `X-Forwarded-Proto: https` for HTTPS requests and `http` for forwarded
  HTTP requests;
- preserve the original `Host` header;
- accept only trusted proxy-to-container traffic on the frontend port.

The frontend Nginx layer also redirects requests explicitly forwarded as HTTP.
It emits HSTS only when `X-Forwarded-Proto` is `https`, so HSTS is not enabled
before TLS is confirmed and internal health checks continue to work. Do not
trust or forward client-supplied `X-Forwarded-*` headers without overwriting
them at the public proxy.

Nginx limits request bodies to 1 MiB, applies coarse API/auth/email request
limits, and returns HTTP 429 when those limits are exceeded. Redis-backed
application limits remain the authoritative protection for authentication and
email endpoints.

## Operations

- `/health` is the process liveness endpoint.
- `/ready` checks PostgreSQL and Redis and is used for backend readiness.
- Back up the `pgdata` volume before migrations and test restoration regularly.
- Keep image/version updates in reviewed pull requests and run CI before release.
- Roll back by deploying the previous application image. Database migrations
  must be reviewed for backward compatibility before every release.

### Monitoring and logs

Set `SENTRY_DSN` to enable Sentry for FastAPI and Celery. Set `APP_RELEASE` to
the deployed Git commit and start with `SENTRY_TRACES_SAMPLE_RATE=0`; increase
sampling only after reviewing volume and cost. Sentry is configured without
default PII and strips headers, cookies, request bodies, and query strings.

Application logs are JSON on stdout for collection by the hosting platform.
They intentionally exclude passwords, authorization headers, cookies, reset
tokens, refresh tokens, SMTP credentials, request bodies, and email addresses.
Restrict log access and define retention in the hosting platform.

Configure an external uptime service to check:

- `GET https://your-domain.example/health` every minute for process liveness;
- `GET https://your-domain.example/ready` every minute for PostgreSQL and Redis
  readiness.

Alert after two consecutive failures and route alerts to an actively monitored
channel. `/ready` should return HTTP 503/500 when a dependency is unavailable;
do not treat `/health` alone as deployment readiness.

### Database backup and restore

Use managed PostgreSQL with encryption, private networking, automated daily
backups, point-in-time recovery, and retention that matches business needs.
Before every migration, create a provider snapshot and record its identifier in
the release notes.

Test restoration at least quarterly into an isolated, non-production database:

1. Restore the selected snapshot or point in time.
2. Connect using a read-only validation account.
3. Confirm Alembic version, table counts, and representative application data.
4. Run `/ready` and the deployment smoke tests against the isolated restore.
5. Delete the temporary restore after recording the result.

For a failed application release, redeploy the previous image. Prefer a
forward-fix for schema problems. Do not run `alembic downgrade` in production
unless the specific downgrade was tested against a copy of production data.
If a destructive migration fails, stop writes and restore the pre-migration
snapshot according to the provider runbook.
