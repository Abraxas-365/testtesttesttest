#!/usr/bin/env bash
#
# Integration test for the full Task Manager stack.
#
# Brings up the docker-compose stack (Go API + nginx-served React frontend),
# waits for both services to report healthy, then exercises the end-to-end
# request flow THROUGH the nginx proxy (the only port published to the host).
#
# Prerequisites on the host: docker, docker compose, curl, jq.
#
set -euo pipefail

# Always run from the repo root (directory of this script).
cd "$(dirname "$0")"

# Host port that the nginx "web" service is published on (see docker-compose.yml).
# In a normal environment the tests run against this published port. When the
# test runner is itself a Docker container that shares the host's daemon (so
# published ports are NOT on this container's localhost), resolve_base_url()
# transparently falls back to reaching the "web" service over the compose
# network instead. WEB is assigned by resolve_base_url() after the stack is up.
WEB=""
PUBLISHED_WEB="http://localhost:8081"

# Network this container joined (for cleanup), if any.
JOINED_NET=""

PASS=0
FAIL=0

pass() { echo "PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1"; FAIL=$((FAIL + 1)); }

require() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: required command '$1' is not installed on the host." >&2
    exit 1
  }
}

cleanup() {
  echo
  echo "--- Cleaning up containers and volumes ---"
  # If we joined the compose network to reach the stack, leave it first.
  if [[ -n "$JOINED_NET" ]]; then
    local self
    self="$(self_container_id || true)"
    [[ -n "$self" ]] && docker network disconnect "$JOINED_NET" "$self" 2>/dev/null || true
  fi
  docker compose down -v --remove-orphans || true
}
trap cleanup EXIT

# self_container_id prints this process's container ID if we are running inside
# a container, otherwise prints nothing.
self_container_id() {
  if [[ -f /proc/self/cgroup ]]; then
    local id
    id="$(grep -oE '[0-9a-f]{64}' /proc/self/cgroup 2>/dev/null | head -1)"
    [[ -n "$id" ]] && { echo "$id"; return 0; }
  fi
  # Fallback: the short hostname is the container ID for default Docker setups.
  local hn
  hn="$(cat /etc/hostname 2>/dev/null || hostname)"
  if docker inspect "$hn" >/dev/null 2>&1; then
    echo "$hn"
  fi
}

# resolve_base_url determines a reachable base URL for the nginx web service and
# assigns it to the global WEB. It prefers the published host port; if that is
# unreachable (e.g. running from a sibling container), it joins the compose
# network and targets the service by name.
resolve_base_url() {
  if curl -fsS -m 3 -o /dev/null "$PUBLISHED_WEB/"; then
    WEB="$PUBLISHED_WEB"
    echo "Using published host port: $WEB"
    return 0
  fi

  echo "Published port $PUBLISHED_WEB is not reachable; trying the compose network..."
  local self net
  self="$(self_container_id || true)"
  if [[ -z "$self" ]]; then
    echo "ERROR: web service is not reachable on $PUBLISHED_WEB and we are not running in a container to join the compose network." >&2
    return 1
  fi
  net="$(docker inspect -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}' "$(docker compose ps -q web)")"
  if [[ -z "$net" ]]; then
    echo "ERROR: could not determine the compose network for the web service." >&2
    return 1
  fi
  docker network connect "$net" "$self" 2>/dev/null || true
  JOINED_NET="$net"
  if curl -fsS -m 5 -o /dev/null "http://web/"; then
    WEB="http://web"
    echo "Reaching web service over compose network '$net' as: $WEB"
    return 0
  fi
  echo "ERROR: web service is not reachable over the compose network." >&2
  return 1
}

# ---- Preflight ----
require docker
require curl
require jq
docker compose version >/dev/null 2>&1 || {
  echo "ERROR: 'docker compose' plugin is not available." >&2
  exit 1
}

# ---- Wait for a service to become healthy ----
wait_healthy() {
  local svc="$1"
  local attempts=40
  local cid
  for ((i = 1; i <= attempts; i++)); do
    cid="$(docker compose ps -q "$svc" 2>/dev/null || true)"
    if [[ -n "$cid" ]]; then
      local status
      status="$(docker inspect -f '{{ if .State.Health }}{{ .State.Health.Status }}{{ else }}{{ .State.Status }}{{ end }}' "$cid" 2>/dev/null || echo "unknown")"
      case "$status" in
        healthy | running)
          echo "service '$svc' is $status"
          return 0
          ;;
        unhealthy | exited | dead)
          echo "ERROR: service '$svc' is '$status'." >&2
          docker compose logs "$svc" || true
          return 1
          ;;
      esac
    fi
    sleep 3
  done
  echo "ERROR: timed out waiting for service '$svc' to become healthy." >&2
  docker compose logs "$svc" || true
  return 1
}

echo "=== Building and starting the stack ==="
docker compose up -d --build

echo
echo "=== Waiting for services to be healthy ==="
wait_healthy api
wait_healthy web

echo
echo "=== Resolving a reachable base URL for the web service ==="
resolve_base_url

echo
echo "=== Running integration tests (through nginx at $WEB) ==="

# 1. The SPA index is served by nginx.
if curl -fsS "$WEB/" | grep -qi '<div id="root"></div>'; then
  pass "SPA index.html is served by nginx"
else
  fail "SPA index.html is served by nginx"
fi

# 2. Create a task via the nginx -> api proxy.
CREATE_BODY='{"title":"Integration test task","description":"created via test.sh"}'
CREATE_RES="$(curl -fsS -X POST "$WEB/api/tasks" \
  -H 'Content-Type: application/json' \
  -d "$CREATE_BODY")"
NEW_ID="$(echo "$CREATE_RES" | jq -r '.id')"
if [[ -n "$NEW_ID" && "$NEW_ID" != "null" ]]; then
  pass "POST /api/tasks created task id=$NEW_ID through nginx proxy"
else
  fail "POST /api/tasks did not return a valid id (response: $CREATE_RES)"
fi

# 3. The created task title round-trips correctly.
if [[ "$(echo "$CREATE_RES" | jq -r '.title')" == "Integration test task" ]]; then
  pass "Created task has the expected title"
else
  fail "Created task title mismatch (response: $CREATE_RES)"
fi

# 4. List tasks and confirm the new task is present.
LIST_RES="$(curl -fsS "$WEB/api/tasks")"
if echo "$LIST_RES" | jq -e --arg id "$NEW_ID" 'map(.id == ($id | tonumber)) | any' >/dev/null; then
  pass "GET /api/tasks lists the created task through nginx proxy"
else
  fail "GET /api/tasks did not list task id=$NEW_ID (response: $LIST_RES)"
fi

# 5. Toggle the task done via PUT through the proxy.
UPDATE_RES="$(curl -fsS -X PUT "$WEB/api/tasks/$NEW_ID" \
  -H 'Content-Type: application/json' \
  -d '{"done":true}')"
if [[ "$(echo "$UPDATE_RES" | jq -r '.done')" == "true" ]]; then
  pass "PUT /api/tasks/$NEW_ID marked the task done through nginx proxy"
else
  fail "PUT did not mark the task done (response: $UPDATE_RES)"
fi

# 6. Delete the task (cleanup of test data) and confirm 204.
DEL_CODE="$(curl -fsS -o /dev/null -w '%{http_code}' -X DELETE "$WEB/api/tasks/$NEW_ID")"
if [[ "$DEL_CODE" == "204" ]]; then
  pass "DELETE /api/tasks/$NEW_ID returned 204 through nginx proxy"
else
  fail "DELETE returned $DEL_CODE (expected 204)"
fi

echo
echo "=== Results: $PASS passed, $FAIL failed ==="
if [[ "$FAIL" -ne 0 ]]; then
  exit 1
fi
echo "All integration tests passed."
