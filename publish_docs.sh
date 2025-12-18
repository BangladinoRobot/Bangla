#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
mkdir -p docs/ildottorpalinsesto

# Copia i dati generati dalla pipeline nella cartella pubblicata da GitHub Pages
for f in stats_checked.json stats_summary.json passed_fixtures_stats.json odds_results.json; do
  if [ -f "$f" ]; then
    cp -f "$f" "docs/ildottorpalinsesto/$f"
  fi
done

# Add solo i JSON in docs
git add docs/ildottorpalinsesto/*.json 2>/dev/null || true

# Commit solo se ci sono cambi
if git diff --cached --quiet; then
  echo "Niente da pubblicare (nessuna modifica)."
  exit 0
fi

git commit -m "Aggiorna dati dashboard (auto)"
git push
echo "OK: pubblicato su GitHub Pages"
