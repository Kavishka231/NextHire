# Production deployment automation

NextHire promotes an immutable Git commit through CI, GHCR, and a production
Docker Compose host. A release is never rebuilt during deployment.

```text
Push to main
    -> CI tests, migrations, browser tests, scans, and image build
    -> build backend/frontend images from the successful commit
    -> block fixable HIGH/CRITICAL vulnerabilities with Trivy
    -> generate and publish service-level CycloneDX SBOMs
    -> tag both images with the full Git SHA
    -> push images to GHCR
    -> production environment approval
    -> SSH to deployment host and check out the same Git SHA
    -> checksummed PostgreSQL backup
    -> controlled Alembic migration
    -> start the immutable images
    -> /health and /ready verification
    -> authenticated deployment smoke test
    -> record successful and previous release SHAs
```

If pull, migration, startup, health, or smoke verification fails,
`scripts/deploy.sh` invokes `scripts/rollback.sh`. Application services return
to the previously successful image SHA and health checks run again. Database
migrations are never automatically downgraded; every production migration must
remain compatible with the previous application release so this rollback is
safe.

## Deployment host prerequisites

Install Git, Docker Engine with Compose v2, Python 3, and curl. Clone the public
repository into the absolute `DEPLOY_PATH`. Create the production `.env` from
`.env.example`, restrict it to the deployment account, and log that account in
to GHCR with a read-only package token:

```sh
printf '%s' "$GHCR_READ_TOKEN" | docker login ghcr.io -u YOUR_GITHUB_USER --password-stdin
chmod 600 .env
mkdir -p .deploy
chmod 700 .deploy
```

Create `.deploy/smoke.env` on the host; it is ignored by Git and is never sent
through workflow command arguments:

```sh
SMOKE_ADMIN_EMAIL=dedicated-smoke-admin@example.com
SMOKE_ADMIN_PASSWORD=replace-with-secret
SMOKE_EMAIL_DOMAIN=controlled-test.example.com
```

Set mode `600`. Use a dedicated least-privilege smoke administrator and a
controlled mailbox/domain because the smoke test creates and deletes data and
queues an email.

The production GitHub Environment requires reviewer approval and these values:

| Type | Name | Purpose |
| --- | --- | --- |
| Secret | `DEPLOY_HOST` | SSH hostname or IP |
| Secret | `DEPLOY_USER` | Restricted deployment account |
| Secret | `DEPLOY_PATH` | Absolute repository path on the host |
| Secret | `DEPLOY_SSH_KEY` | Private key for that account |
| Secret | `DEPLOY_KNOWN_HOSTS` | Pre-verified SSH host-key line |
| Variable | `PUBLIC_BASE_URL` | Public HTTPS origin |

Do not generate `known_hosts` dynamically inside CI. Verify the host key over a
separate trusted channel before storing it. Restrict the SSH key to the one
deployment host and protect the production Environment with required reviewers.

## Manual operation

The same automation can be invoked on the host without GitHub Actions:

```sh
export IMAGE_REPOSITORY=ghcr.io/owner/nexthire
export IMAGE_TAG=FULL_40_CHARACTER_GIT_SHA
export PUBLIC_BASE_URL=https://jobs.example.com
export RUN_DEPLOYMENT_SMOKE=true
./scripts/deploy.sh
```

Manual rollback uses the recorded prior release:

```sh
export IMAGE_REPOSITORY=ghcr.io/owner/nexthire
export PUBLIC_BASE_URL=https://jobs.example.com
./scripts/rollback.sh
```

To target a reviewed release explicitly, set `ROLLBACK_TAG` to its full image
tag. Rollback changes application containers only; use the database recovery
runbook for data loss or an incompatible schema incident.

## Release evidence and failure handling

Retain the CI run, image SHA tags/digests, approval, backup identifier, Alembic
revision, health output, smoke-test output, and deployed SHA. Alert when the
workflow or rollback fails. If automatic rollback cannot restore health, stop
traffic, preserve logs and the backup, and follow `DATABASE_RECOVERY.md`.

Container vulnerability gating and SBOM evidence are detailed in
[`CONTAINER_SUPPLY_CHAIN.md`](CONTAINER_SUPPLY_CHAIN.md).
