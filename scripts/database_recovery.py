#!/usr/bin/env python3
"""Create, restore, and verify NextHire PostgreSQL backups through Docker Compose."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class RecoveryError(RuntimeError):
    pass


def environment() -> dict[str, str]:
    values = {"POSTGRES_USER": "nexthire", "POSTGRES_DB": "nexthire"}
    env_file = ROOT / ".env"
    if env_file.exists():
        for raw in env_file.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    values.update({key: value for key, value in os.environ.items() if value})
    return values


def compose(*args: str) -> list[str]:
    return ["docker", "compose", *args]


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(command, cwd=ROOT, check=True, **kwargs)
    except FileNotFoundError as exc:
        raise RecoveryError("Docker Compose is required and was not found") from exc
    except subprocess.CalledProcessError as exc:
        raise RecoveryError(f"Command failed with exit code {exc.returncode}") from exc


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def backup(args: argparse.Namespace) -> None:
    env = environment()
    user, database = env["POSTGRES_USER"], env["POSTGRES_DB"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"nexthire-{database}-{stamp}.dump"
    temporary = output.with_suffix(".dump.partial")
    command = compose("exec", "-T", "db", "pg_dump", "--username", user,
                      "--dbname", database, "--format=custom", "--compress=9",
                      "--no-owner", "--no-privileges")
    try:
        with temporary.open("wb") as destination:
            run(command, stdout=destination, stderr=subprocess.PIPE)
        if temporary.stat().st_size == 0:
            raise RecoveryError("pg_dump produced an empty backup")
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)

    sha256 = digest(output)
    output.with_suffix(".dump.sha256").write_text(f"{sha256}  {output.name}\n", encoding="ascii")
    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(), "database": database,
        "postgres_user": user, "format": "pg_dump custom", "sha256": sha256,
        "size_bytes": output.stat().st_size,
    }
    output.with_suffix(".dump.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Backup created: {output}")
    print(f"SHA-256: {sha256}")
    print("Copy the dump, checksum, and metadata to encrypted off-site storage.")


def verify_checksum(backup_file: Path) -> None:
    checksum_file = backup_file.with_suffix(backup_file.suffix + ".sha256")
    if not checksum_file.exists():
        raise RecoveryError(f"Missing checksum file: {checksum_file}")
    expected = checksum_file.read_text(encoding="ascii").split()[0]
    if digest(backup_file) != expected:
        raise RecoveryError("Backup checksum mismatch; do not restore this file")


def database_table_count(user: str, database: str) -> int:
    result = run(compose("exec", "-T", "db", "psql", "--username", user,
                         "--dbname", database, "-tAc",
                         "SELECT count(*) FROM pg_tables WHERE schemaname='public'"),
                 text=True, capture_output=True)
    return int(result.stdout.strip())


def restore(args: argparse.Namespace) -> None:
    env = environment()
    user, database = env["POSTGRES_USER"], env["POSTGRES_DB"]
    backup_file = args.backup.resolve()
    if not backup_file.is_file():
        raise RecoveryError(f"Backup does not exist: {backup_file}")
    if args.confirm_database != database:
        raise RecoveryError(f"Refusing restore: pass --confirm-database {database}")
    verify_checksum(backup_file)
    if database_table_count(user, database) != 0:
        raise RecoveryError("Target database is not empty. Restore into a new isolated database; this tool never deletes existing data.")
    command = compose("exec", "-T", "db", "pg_restore", "--username", user,
                      "--dbname", database, "--exit-on-error", "--single-transaction",
                      "--no-owner", "--no-privileges")
    with backup_file.open("rb") as source:
        run(command, stdin=source)
    print(f"Restore completed into empty database: {database}")
    print("Run the verify command before allowing application traffic.")


def verify(args: argparse.Namespace) -> None:
    env = environment()
    user, database = env["POSTGRES_USER"], env["POSTGRES_DB"]
    count = database_table_count(user, database)
    if count == 0:
        raise RecoveryError("Restored database has no public tables")
    migration = run(compose("exec", "-T", "db", "psql", "--username", user,
                            "--dbname", database, "-tAc",
                            "SELECT version_num FROM alembic_version"),
                    text=True, capture_output=True).stdout.strip()
    if migration != args.expected_head:
        raise RecoveryError(f"Migration is {migration or 'missing'}, expected {args.expected_head}")
    print(f"Database verification passed: {count} tables, migration {migration}")
    if args.base_url:
        for endpoint in ("/health", "/ready"):
            with urllib.request.urlopen(f"{args.base_url.rstrip('/')}{endpoint}", timeout=10) as response:
                if response.status != 200:
                    raise RecoveryError(f"{endpoint} returned HTTP {response.status}")
            print(f"Application verification passed: {endpoint}")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    create = commands.add_parser("backup", help="create a checksummed custom-format dump")
    create.add_argument("--output-dir", type=Path, default=ROOT / "backups")
    create.set_defaults(handler=backup)
    load = commands.add_parser("restore", help="restore into an empty configured database")
    load.add_argument("backup", type=Path)
    load.add_argument("--confirm-database", required=True)
    load.set_defaults(handler=restore)
    check = commands.add_parser("verify", help="verify restored schema and optional application health")
    check.add_argument("--expected-head", default="013")
    check.add_argument("--base-url")
    check.set_defaults(handler=verify)
    return root


def main() -> int:
    try:
        args = parser().parse_args()
        args.handler(args)
        return 0
    except (RecoveryError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
