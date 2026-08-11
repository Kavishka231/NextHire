import argparse
import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "database_recovery.py"
SPEC = importlib.util.spec_from_file_location("database_recovery", SCRIPT)
recovery = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(recovery)


def write_backup(tmp_path: Path, content: bytes = b"postgres backup") -> Path:
    backup = tmp_path / "backup.dump"
    backup.write_bytes(content)
    checksum = recovery.digest(backup)
    backup.with_suffix(".dump.sha256").write_text(
        f"{checksum}  {backup.name}\n", encoding="ascii"
    )
    return backup


def test_checksum_accepts_untampered_backup(tmp_path):
    recovery.verify_checksum(write_backup(tmp_path))


def test_checksum_rejects_tampered_backup(tmp_path):
    backup = write_backup(tmp_path)
    backup.write_bytes(b"tampered")
    with pytest.raises(recovery.RecoveryError, match="checksum mismatch"):
        recovery.verify_checksum(backup)


def test_restore_requires_exact_database_confirmation(tmp_path, monkeypatch):
    backup = write_backup(tmp_path)
    monkeypatch.setattr(
        recovery,
        "environment",
        lambda: {"POSTGRES_USER": "nexthire", "POSTGRES_DB": "production"},
    )
    with pytest.raises(recovery.RecoveryError, match="--confirm-database production"):
        recovery.restore(argparse.Namespace(backup=backup, confirm_database="wrong"))


def test_restore_refuses_nonempty_database(tmp_path, monkeypatch):
    backup = write_backup(tmp_path)
    monkeypatch.setattr(
        recovery,
        "environment",
        lambda: {"POSTGRES_USER": "nexthire", "POSTGRES_DB": "production"},
    )
    monkeypatch.setattr(recovery, "database_table_count", lambda *_: 13)
    with pytest.raises(recovery.RecoveryError, match="not empty"):
        recovery.restore(argparse.Namespace(backup=backup, confirm_database="production"))
