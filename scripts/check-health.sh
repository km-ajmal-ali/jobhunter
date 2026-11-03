#!/usr/bin/env bash
# =============================================================================
# Health/OOM Watchdog for JobHunter
#
# Checks container health + OOM status, alerts via webhook if something's wrong.
# Meant to run on a schedule (cron), not continuously.
#
# Usage:
#   bash scripts/check-health.sh
#
# Cron (every 5 min):
#   */5 * * * * /opt/jobhunter/scripts/check-health.sh >> /var/log/jobhunter-health.log 2>&1
#
# Optional: set ALERT_WEBHOOK_URL in .env for Slack/Discord-style webhook alerts.
# =============================================================================

set -euo pipefail

ENV_FILE="${ENV_FILE:-/opt/jobhunter/.env}"
[ -f "$ENV_FILE" ] && source "$ENV_FILE"

CONTAINERS=("jobhunter-db" "jobhunter-backend" "jobhunter-frontend")
PROBLEMS=()

alert() {
  local msg="$1"
  echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] ALERT: $msg"
  if [ -n "${ALERT_WEBHOOK_URL:-}" ]; then
    curl -fsSL -X POST "$ALERT_WEBHOOK_URL" \
      -H 'Content-Type: application/json' \
      -d "{\"content\": \"🚨 JobHunter: $msg\", \"text\": \"🚨 JobHunter: $msg\"}" >/dev/null 2>&1 || true
  fi
}

for name in "${CONTAINERS[@]}"; do
  if ! docker inspect "$name" >/dev/null 2>&1; then
    PROBLEMS+=("$name: container not found")
    continue
  fi

  running=$(docker inspect -f '{{.State.Running}}' "$name")
  oom_killed=$(docker inspect -f '{{.State.OOMKilled}}' "$name")
  restart_count=$(docker inspect -f '{{.RestartCount}}' "$name")
  exit_code=$(docker inspect -f '{{.State.ExitCode}}' "$name")

  if [ "$oom_killed" = "true" ]; then
    PROBLEMS+=("$name: OOM-killed (restart count: $restart_count)")
  fi

  if [ "$running" != "true" ]; then
    PROBLEMS+=("$name: not running (exit code: $exit_code)")
  fi
done

# Kernel-level OOM check (catches host-level kills docker may not attribute)
if command -v dmesg >/dev/null 2>&1; then
  recent_oom=$(dmesg -T 2>/dev/null | grep -i "killed process" | tail -5 || true)
  if [ -n "$recent_oom" ]; then
    PROBLEMS+=("kernel OOM killer fired recently:"$'\n'"$recent_oom")
  fi
fi

if [ ${#PROBLEMS[@]} -eq 0 ]; then
  echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] OK: all containers healthy"
else
  for p in "${PROBLEMS[@]}"; do
    alert "$p"
  done
  exit 1
fi
