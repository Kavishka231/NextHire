# Deployment smoke test

Run this suite against an isolated staging environment using the exact images,
proxy configuration, PostgreSQL version, Redis version, worker, scheduler, and
environment-variable shape intended for production. Never run it against live
customer data without an approved maintenance window.

## Prerequisites

- Migration `013` is current.
- `/health` and `/ready` are healthy through the public HTTPS proxy.
- A dedicated super-administrator account exists.
- A controlled email domain or catch-all mailbox accepts generated test
  addresses.
- SMTP, the Celery worker, and Celery beat are running.
- The operator can inspect application, worker, proxy, PostgreSQL, Redis, and
  Brevo delivery logs.

Do not put administrator credentials on a shared command line or in shell
history. Prefer temporary environment variables supplied by the CI/CD secret
store:

```powershell
python scripts/deployment_smoke.py --confirm-write-tests
```

The runner reads `SMOKE_BASE_URL`, `SMOKE_ADMIN_EMAIL`,
`SMOKE_ADMIN_PASSWORD`, and `SMOKE_EMAIL_DOMAIN`. The deployment can override
the default `nexthire_refresh` cookie name with `--refresh-cookie-name`.

The runner creates uniquely named candidate and employer accounts, approves the
employer, creates and updates a job, searches and saves it, creates a note and
application, tests refresh rotation, changes the password, requests a reset
email, logs out, and removes temporary users and jobs. If it reports a cleanup
warning, remove the listed records before continuing.

## Manual evidence

Record the release commit, image digests, test time, operator, and result for
each check. Never record passwords, reset tokens, cookies, or authorization
headers.

### Password-reset delivery

1. Confirm the generated candidate receives exactly one reset email.
2. Confirm the link uses the public HTTPS domain.
3. Open the link and set a new test password.
4. Confirm the token cannot be reused and the prior refresh session is rejected.
5. Confirm Brevo reports delivery without bounce, block, or complaint.

### Celery reminder

Use an isolated database copy or a dedicated fixture to make a smoke candidate's
`applied` saved job older than seven days. Run:

```powershell
docker compose exec worker celery -A tasks.celery_app call tasks.reminder_task.send_reminders
```

Confirm the worker reports success, one reminder reaches the controlled mailbox,
and no password, token, credential, authorization header, or full email address
appears in logs. Do not age or edit real customer records.

### Database restart and recovery

1. Keep the frontend, API, Redis, worker, and scheduler running.
2. Restart only PostgreSQL: `docker compose restart db`.
3. During restart, confirm `/health` remains a liveness signal and `/ready`
   becomes unhealthy.
4. Confirm the API container does not enter an uncontrolled restart loop.
5. Wait for PostgreSQL health, then require `/ready` to recover.
6. Re-run the automated smoke runner and confirm existing test data remains
   readable.
7. Inspect API, worker, scheduler, and PostgreSQL logs for connection-pool
   recovery and unexpected errors.

### Browser and role checks

Repeat the candidate, employer, and administrator paths through the deployed
frontend in a supported desktop and mobile browser. Confirm secure refresh
cookies are `HttpOnly`, `Secure`, and `SameSite=Lax`; logout clears the cookie;
browser developer tools show no mixed content; and security headers are present.

## Release decision

Do not deploy or open registration if any required workflow fails, temporary
records cannot be removed, `/ready` does not recover after PostgreSQL returns,
mail is rejected, or secrets appear in logs. Record the failure, roll back the
application image when appropriate, and repeat the full suite after the fix.

The following are tracked as post-launch product work rather than release
blockers: native resume upload, new-account email verification, employer
document verification, account deletion and data export, large-collection
pagination, richer application notifications, expanded accessibility/browser
testing, and privacy/terms/cookie content.
