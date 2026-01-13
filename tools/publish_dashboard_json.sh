#!/usr/bin/env bash
set -euo pipefail

export GIT_TERMINAL_PROMPT=0
export SSH_ASKPASS=/bin/false

cd "$(dirname "$0")/.."

echo "[publish_dashboard_json] $(date -Is) start"

# 1) rigenera SEMPRE i JSON della dashboard (se fallisce, esce con log utile)
python3 tools/build_dashboard_data.py

# 2) stage dei file rilevanti (best-effort)
git add \
  docs/ildottorpalinsesto/data/*.json \
  docs/ildottorpalinsesto/stats_checked.json \
  docs/ildottorpalinsesto/passed_fixtures_stats.json \
  docs/ildottorpalinsesto/odds_results.json \
  2>/dev/null || true

# 3) se non c'è nulla da committare, stop
if git diff --cached --quiet; then
  echo "[publish_dashboard_json] no changes"
  exit 0
fi

ts="$(date +%Y%m%d_%H%M%S)"
git commit -m "auto: update dashboard data ${ts}" >/dev/null 2>&1 || {
  echo "[publish_dashboard_json] commit failed (nothing to commit?)"
  exit 0
}

GIT_SSH_COMMAND="ssh -o BatchMode=yes" git push >/dev/null 2>&1 || {
  echo "[publish_dashboard_json] push failed"
  exit 0
}

echo "[publish_dashboard_json] pushed"
