#!/usr/bin/env bash
#
# Integration test for the Task Manager full stack.
#
# It builds and starts the docker-compose stack (Go API + nginx/React web),
# then verifies the full request path end to end:
#
#   1. Wait for the web (nginx) and api services to become healthy.
#   2. Create a task by POSTing through nginx (/api/tasks) -> Go API.
#   3. GET /api/tasks through nginx and assert the new task appears.
#   4. Confirm the web service serves the SPA index.html.
#   5. Tear the stack down (containers + volumes) on exit.
#
# All requests are issued from a throwaway container attached to the compose
# network, so the test does not depend on host port publishing being reachable
# from wherever the script runs.
set -uo pipefail

cd "$(dirname "$0")"

PROJECT="taskmgr_itest"
COMPOSE=(docker compose -p "$PROJECT")
NETWORK="${PROJECT}_default"
# Lightweight image used to run curl from inside the compose network.
CURL_IMG="curlimages/curl:8.10.1"

PASS=0
FAIL=0

log()  { printf '\n>>> %s\n' "$*"; }
ok()   { printf '    [PASS] %s\n' "$*"; PASS=$((PASS+1)); }
bad()  { printf '    [FAIL] %s\n' "$*"; FAIL=$((FAIL+1)); }

cleanup() {
  log "Cleaning up: docker compose down -v"
  "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

# Run curl inside the compose network. Usage: incurl <curl args...>
incurl() {
  docker run --rm --network "$NETWORK" "$CURL_IMG" -s "$@"
}

log "Docker / Compose versions"
docker --version
docker compose version

log "Building and starting the stack (docker compose up -d --build)"
if ! "${COMPOSE[@]}" up -d --build; then
  bad "docker compose up failed"
  "${COMPOSE[@]}" ps
  exit 1
fi
ok "compose stack started"

# Pre-pull the curl helper image so timing/output is clean.
docker pull -q "$CURL_IMG" >/dev/null 2>&1 || true

log "Waiting for services to become healthy"
wait_healthy() {
  local svc="$1" cid status
  cid="$("${COMPOSE[@]}" ps -q "$svc")"
  if [ -z "$cid" ]; then bad "service '$svc' has no container"; return 1; fi
  for _ in $(seq 1 40); do
    status="$(docker inspect -f '{{ if .State.Health }}{{ .State.Health.Status }}{{ else }}{{ .State.Status }}{{ end }}' "$cid" 2>/dev/null)"
    case "$status" in
      healthy|running) ok "service '$svc' is $status"; return 0 ;;
      unhealthy|exited|dead) bad "service '$svc' is $status"; return 1 ;;
    esac
    sleep 3
  done
  bad "service '$svc' did not become healthy in time (last: ${status:-unknown})"
  return 1
}

if ! wait_healthy api;  then "${COMPOSE[@]}" logs api;  exit 1; fi
if ! wait_healthy web;  then "${COMPOSE[@]}" logs web;  exit 1; fi

TITLE="integration-test-task-$(date +%s)"
DESC="created by test.sh"

log "Creating a task via nginx (POST http://web/api/tasks)"
CREATE_RESP="$(incurl -X POST http://web/api/tasks \
  -H 'Content-Type: application/json' \
  -d "{\"title\":\"${TITLE}\",\"description\":\"${DESC}\"}")"
echo "    response: ${CREATE_RESP}"

NEW_ID="$(printf '%s' "$CREATE_RESP" | jq -r '.id // empty' 2>/dev/null)"
if [ -n "$NEW_ID" ] && printf '%s' "$CREATE_RESP" | jq -e --arg t "$TITLE" '.title == $t' >/dev/null 2>&1; then
  ok "task created with id=${NEW_ID}"
else
  bad "task creation did not return expected JSON"
fi

log "Listing tasks via nginx (GET http://web/api/tasks)"
LIST_RESP="$(incurl http://web/api/tasks)"
echo "    response: ${LIST_RESP}"

if printf '%s' "$LIST_RESP" | jq -e --arg t "$TITLE" 'any(.[]; .title == $t)' >/dev/null 2>&1; then
  ok "created task appears in GET /api/tasks"
else
  bad "created task NOT found in GET /api/tasks"
fi

log "Verifying nginx serves the SPA (GET http://web/)"
INDEX_RESP="$(incurl http://web/)"
if printf '%s' "$INDEX_RESP" | grep -qi '<div id="root"'; then
  ok "web service serves index.html with #root mount point"
else
  bad "web service did not serve the expected SPA index.html"
fi

log "Verifying API persistence path directly (GET http://api:8080/api/tasks)"
API_DIRECT="$(incurl http://api:8080/api/tasks)"
if printf '%s' "$API_DIRECT" | jq -e --arg t "$TITLE" 'any(.[]; .title == $t)' >/dev/null 2>&1; then
  ok "task also visible directly from the Go API container"
else
  bad "task not visible directly from the Go API container"
fi

log "RESULTS: ${PASS} passed, ${FAIL} failed"
if [ "$FAIL" -ne 0 ]; then
  echo "INTEGRATION TEST FAILED"
  exit 1
fi
echo "INTEGRATION TEST PASSED"
exit 0
