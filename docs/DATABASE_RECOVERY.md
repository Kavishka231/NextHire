# PostgreSQL backup and disaster recovery

This runbook answers the production failure case: **PostgreSQL and its host are
lost.** Backups must survive the database, Docker host, cloud account mistakes,
and operator error.

```text
Production PostgreSQL
        ↓
pg_dump backup + SHA-256 + metadata
        ↓
Encrypted, access-controlled off-site storage
        ↓
Restore into a new empty PostgreSQL database
        ↓
Verify checksum, schema, Alembic head 013, and representative data
        ↓
Start application and verify /health, /ready, and smoke workflows
        ↓
Switch traffic only after approval
```

## Backup policy

- Use managed PostgreSQL automated backups and point-in-time recovery as the
  primary control. Keep daily backups for at least 30 days, or longer when
  contractual and legal requirements demand it.
- Run the portable logical backup before every migration and at least daily.
- Store the `.dump`, `.sha256`, and `.json` files together in encrypted object
  storage outside the database host. Enable object versioning or immutability
  and restrict deletion to a separate recovery role.
- Monitor the scheduled backup job and alert on failure, missing uploads,
  unexpected size changes, or an expired latest recovery point.

From the deployment directory, while PostgreSQL is healthy:

```powershell
python scripts/database_recovery.py backup
```

The script streams a PostgreSQL custom-format dump without putting credentials
on the command line. It writes to the ignored `backups/` directory, calculates
SHA-256, records non-secret metadata, and never modifies the database. Upload
all three generated files, then verify the remote size and checksum.

## Restore procedure

Restoration is intentionally guarded. The script refuses a database containing
any public tables and never drops or cleans an existing database.

1. Declare an incident, stop writes, record the last known good recovery point,
   and preserve logs. Do not destroy the failed database.
2. Provision a new isolated PostgreSQL 15 instance with encrypted storage and
   private networking.
3. Download the selected `.dump`, `.dump.sha256`, and `.dump.json` files from
   off-site storage. Review timestamp, source database, size, and retention.
4. Configure `.env` for the isolated database and start only PostgreSQL:

   ```powershell
   docker compose up -d db
   python scripts/database_recovery.py restore backups/nexthire-nexthire-TIMESTAMP.dump --confirm-database nexthire
   ```

5. Verify schema and migration state before starting application services:

   ```powershell
   python scripts/database_recovery.py verify --expected-head 013
   ```

   If the backup predates the deployed release, record its Alembic revision,
   take another snapshot, run `docker compose --profile operations run --rm
   migrate`, and repeat verification. Never improvise a downgrade.
6. Validate table counts and representative users, jobs, applications, and
   audit records with a read-only account. Do not copy sensitive rows into the
   incident ticket.
7. Start the exact release images against the recovered database:

   ```powershell
   docker compose up -d
   python scripts/database_recovery.py verify --expected-head 013 --base-url https://recovery.example.com
   ```

8. Run `scripts/deployment_smoke.py` and `DEPLOYMENT_SMOKE_TEST.md`. Confirm
   authentication, search, saved jobs, employer applications, admin access,
   Celery, and email behavior.
9. Obtain incident-owner approval, switch traffic, monitor errors and data
   consistency, and retain the failed environment until disposal is approved.

## Restore testing and evidence

Perform a recovery exercise at least quarterly. Record:

- backup identifier, timestamp, size, SHA-256, and storage version;
- restore start/end time and achieved recovery time objective (RTO);
- latest recovered transaction time and achieved recovery point objective (RPO);
- PostgreSQL/application versions, Alembic revision, and image digests;
- verification and smoke-test results; and
- operator, reviewer, exceptions, and follow-up actions.

A backup is not valid until a restore test succeeds. Test in an isolated
account/network, restrict access to restored customer data, and securely delete
the exercise environment after evidence is approved.

## Failure handling

- Checksum mismatch: quarantine the object and select an earlier recovery point.
- Restore error: retain logs, create a new empty target, and retry; never restore
  over a partially restored database.
- Wrong migration revision: stop before startup and use the reviewed
  forward-migration plan.
- `/ready` failure: keep traffic disabled and investigate PostgreSQL and Redis.
- Data inconsistency: stop writes, notify the incident owner, and select another
  recovery point or use provider point-in-time recovery.
