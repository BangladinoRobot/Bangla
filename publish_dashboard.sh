#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

mkdir -p docs/ildottorpalinsesto

# copia i JSON “sorgente” dentro GitHub Pages
cp -f stats_summary.json stats_checked.json passed_fixtures_stats.json passed_fixtures_stats_all.json docs/ildottorpalinsesto/ 2>/dev/null || true

git add docs/ildottorpalinsesto/*.json

if git diff --cached --quiet; then
  echo "OK: nulla da pubblicare"
  exit 0
fi

git commit -m "Auto: publish dashboard data $(date -u +%F)" >/dev/null
git push
echo "OK: pubblicato su GitHub"
