#!/usr/bin/env sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
state_dir="$project_dir/.deploy"
previous_file="$state_dir/previous-release"
current_file="$state_dir/current-release"
compose_files="-f docker-compose.yml -f docker-compose.production.yml"

cd "$project_dir"
: "${IMAGE_REPOSITORY:?IMAGE_REPOSITORY is required}"
: "${PUBLIC_BASE_URL:?PUBLIC_BASE_URL is required}"

rollback_tag=${ROLLBACK_TAG:-}
if [ -z "$rollback_tag" ] && [ -f "$previous_file" ]; then
  rollback_tag=$(cat "$previous_file")
fi
if [ -z "$rollback_tag" ]; then
  echo "No previous release is recorded; manual recovery is required" >&2
  exit 1
fi

case "$rollback_tag" in *[!A-Za-z0-9_.-]*|'') echo "Invalid rollback tag" >&2; exit 2 ;; esac

failed_tag=""
if [ -f "$current_file" ]; then failed_tag=$(cat "$current_file"); fi
export IMAGE_TAG=$rollback_tag
docker compose $compose_files pull backend worker scheduler frontend
docker compose $compose_files up -d --no-build backend worker scheduler frontend
"$project_dir/scripts/health-check.sh" "$PUBLIC_BASE_URL"

printf '%s\n' "$rollback_tag" > "$current_file"
if [ -n "$failed_tag" ] && [ "$failed_tag" != "$rollback_tag" ]; then
  printf '%s\n' "$failed_tag" > "$previous_file"
fi
echo "Rollback completed: $rollback_tag"
