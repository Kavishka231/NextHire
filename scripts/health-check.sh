#!/usr/bin/env sh
set -eu

base_url=${1:-${PUBLIC_BASE_URL:-}}
attempts=${HEALTH_CHECK_ATTEMPTS:-30}
delay=${HEALTH_CHECK_DELAY_SECONDS:-5}

if [ -z "$base_url" ]; then
  echo "PUBLIC_BASE_URL or the first argument is required" >&2
  exit 2
fi

base_url=${base_url%/}
case "$base_url" in
  https://*|http://localhost*|http://127.0.0.1*) ;;
  *) echo "Health target must use HTTPS unless it is local" >&2; exit 2 ;;
esac

attempt=1
while [ "$attempt" -le "$attempts" ]; do
  if curl --fail --silent --show-error --max-time 10 "$base_url/health" >/dev/null \
    && curl --fail --silent --show-error --max-time 10 "$base_url/ready" >/dev/null; then
    echo "Health verification passed for $base_url"
    exit 0
  fi
  echo "Health verification attempt $attempt/$attempts failed" >&2
  attempt=$((attempt + 1))
  sleep "$delay"
done

echo "Deployment did not become healthy: $base_url" >&2
exit 1
