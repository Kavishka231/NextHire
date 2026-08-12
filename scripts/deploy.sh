#!/usr/bin/env sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
state_dir="$project_dir/.deploy"
current_file="$state_dir/current-release"
previous_file="$state_dir/previous-release"
pending_file="$state_dir/pending-release"
compose_files="-f docker-compose.yml -f docker-compose.production.yml"

cd "$project_dir"
: "${IMAGE_REPOSITORY:?IMAGE_REPOSITORY is required}"
: "${IMAGE_TAG:?IMAGE_TAG is required}"
: "${PUBLIC_BASE_URL:?PUBLIC_BASE_URL is required}"
case "$IMAGE_TAG" in *[!A-Za-z0-9_.-]*|'') echo "Invalid IMAGE_TAG" >&2; exit 2 ;; esac

mkdir -p "$state_dir"
current_tag=""
if [ -f "$current_file" ]; then current_tag=$(cat "$current_file"); fi
if [ "$current_tag" = "$IMAGE_TAG" ]; then
  echo "Release $IMAGE_TAG is already active"
  "$project_dir/scripts/health-check.sh" "$PUBLIC_BASE_URL"
  exit 0
fi
printf '%s\n' "$IMAGE_TAG" > "$pending_file"

rollback_on_failure() {
  status=$1
  trap - EXIT INT TERM HUP
  rm -f "$pending_file"
  if [ -n "$current_tag" ]; then
    echo "Deployment failed; rolling back application services to $current_tag" >&2
    ROLLBACK_TAG=$current_tag "$project_dir/scripts/rollback.sh" || \
      echo "Automatic rollback failed; manual recovery is required" >&2
  else
    echo "Deployment failed and no previous release is recorded" >&2
  fi
  exit "$status"
}
trap 'rollback_on_failure $?' EXIT
trap 'exit 130' INT TERM HUP

"$project_dir/scripts/backup.sh"
docker compose $compose_files pull migrate backend worker scheduler frontend
docker compose $compose_files --profile operations run --rm migrate
docker compose $compose_files up -d --no-build backend worker scheduler frontend

"$project_dir/scripts/health-check.sh" "$PUBLIC_BASE_URL"

if [ "${RUN_DEPLOYMENT_SMOKE:-false}" = "true" ]; then
  smoke_env_file="$state_dir/smoke.env"
  if [ ! -f "$smoke_env_file" ]; then
    echo "Smoke tests require $smoke_env_file on the deployment host" >&2
    exit 1
  fi
  set -a
  . "$smoke_env_file"
  set +a
  : "${SMOKE_ADMIN_EMAIL:?SMOKE_ADMIN_EMAIL is required when smoke tests are enabled}"
  : "${SMOKE_ADMIN_PASSWORD:?SMOKE_ADMIN_PASSWORD is required when smoke tests are enabled}"
  : "${SMOKE_EMAIL_DOMAIN:?SMOKE_EMAIL_DOMAIN is required when smoke tests are enabled}"
  SMOKE_BASE_URL=$PUBLIC_BASE_URL python3 scripts/deployment_smoke.py --confirm-write-tests
fi

if [ -n "$current_tag" ]; then printf '%s\n' "$current_tag" > "$previous_file"; fi
printf '%s\n' "$IMAGE_TAG" > "$current_file"
rm -f "$pending_file"
trap - EXIT INT TERM HUP
echo "Deployment succeeded: $IMAGE_TAG"
