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
docker compose up -d
docker compose ps
curl --fail http://localhost:5500/
curl --fail http://localhost:5500/api/v1/jobs
```

After deployment, confirm Alembic reports migration `009` as the current head.
Migration `009` intentionally expires refresh tokens created by earlier
versions, so existing users must sign in again after this release.

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
