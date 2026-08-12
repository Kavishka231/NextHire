#!/usr/bin/env sh
set -eu

source_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
test_root=$(mktemp -d)
trap 'rm -rf "$test_root"' EXIT INT TERM HUP
mkdir -p "$test_root/scripts" "$test_root/bin"
cp "$source_root/scripts/deploy.sh" "$source_root/scripts/rollback.sh" \
  "$source_root/scripts/health-check.sh" "$source_root/scripts/backup.sh" \
  "$test_root/scripts/"
touch "$test_root/docker-compose.yml" "$test_root/docker-compose.production.yml"

cat > "$test_root/bin/docker" <<'EOF'
#!/usr/bin/env sh
printf '%s|docker %s\n' "${IMAGE_TAG:-none}" "$*" >> "$DEPLOY_TEST_LOG"
exit 0
EOF
cat > "$test_root/bin/python3" <<'EOF'
#!/usr/bin/env sh
printf '%s|python3 %s\n' "${IMAGE_TAG:-none}" "$*" >> "$DEPLOY_TEST_LOG"
exit 0
EOF
cat > "$test_root/bin/curl" <<'EOF'
#!/usr/bin/env sh
if [ "${IMAGE_TAG:-}" = "${FAIL_TAG:-never}" ]; then exit 22; fi
exit 0
EOF
chmod +x "$test_root/bin/docker" "$test_root/bin/python3" "$test_root/bin/curl" "$test_root/scripts/"*.sh

export PATH="$test_root/bin:$PATH"
export DEPLOY_TEST_LOG="$test_root/deploy.log"
export IMAGE_REPOSITORY="ghcr.io/example/nexthire"
export PUBLIC_BASE_URL="https://jobs.example.com"
export HEALTH_CHECK_ATTEMPTS=1
export HEALTH_CHECK_DELAY_SECONDS=0

good_tag=1111111111111111111111111111111111111111
bad_tag=2222222222222222222222222222222222222222
IMAGE_TAG=$good_tag "$test_root/scripts/deploy.sh"
test "$(cat "$test_root/.deploy/current-release")" = "$good_tag"

export FAIL_TAG=$bad_tag
if IMAGE_TAG=$bad_tag "$test_root/scripts/deploy.sh"; then
  echo "Expected unhealthy deployment to fail" >&2
  exit 1
fi
test "$(cat "$test_root/.deploy/current-release")" = "$good_tag"
grep -q "${good_tag}|docker compose -f docker-compose.yml -f docker-compose.production.yml up" "$DEPLOY_TEST_LOG"

echo "Deployment promotion and automatic rollback tests passed"
