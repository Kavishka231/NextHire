#!/usr/bin/env sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"

python_command=${PYTHON_COMMAND:-python3}
"$python_command" scripts/database_recovery.py backup --output-dir "${BACKUP_DIR:-$project_dir/backups}"
