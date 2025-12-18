#!/bin/bash
cd /home/pi/BangladinoRobot || exit 1
source venv/bin/activate

run_once() {
  python3 screen_league_fixtures.py || return 1
  python3 run_stats_on_league_fixtures.py || return 1
  python3 odds_layer_theoddsapi.py || return 1
# REBUILD_PASSED_FROM_REGISTRY_V1
python3 tools/rebuild_passed_from_registry.py

  python3 ildottorpalinsesto_generate.py || return 1
  return 0
}

MAX_ATTEMPTS=6
DELAY=600  # 10 minuti

attempt=1
while [ $attempt -le $MAX_ATTEMPTS ]; do
  echo "[$(date)] Pipeline calcio, tentativo $attempt" >> cron.log
  if run_once; then
    echo "[$(date)] Pipeline completata con successo" >> cron.log
    exit 0
  fi
  echo "[$(date)] Pipeline fallita (tentativo $attempt)" >> cron.log
  if [ $attempt -lt $MAX_ATTEMPTS ]; then
    sleep $DELAY
  fi
  attempt=$((attempt+1))
done

echo "[$(date)] Pipeline fallita dopo $MAX_ATTEMPTS tentativi" >> cron.log
exit 1

# Post-process dashboard: home senza lista, campionati.html con lista
python3 tools/postprocess_dashboard.py

### JSON_TO_DOCS_V1
# Pubblica i JSON usati dal sito (NO chiamate API dal front-end)
mkdir -p docs/ildottorpalinsesto
cp -a stats_checked.json docs/ildottorpalinsesto/stats_checked.json 2>/dev/null || true
cp -a passed_fixtures_stats.json docs/ildottorpalinsesto/passed_fixtures_stats.json 2>/dev/null || true
cp -a stats_summary.json docs/ildottorpalinsesto/stats_summary.json 2>/dev/null || true

### JSON_TO_DOCS_V2
mkdir -p docs/ildottorpalinsesto
cp -a stats_summary.json docs/ildottorpalinsesto/stats_summary.json 2>/dev/null || true
cp -a stats_checked.json docs/ildottorpalinsesto/stats_checked.json 2>/dev/null || true
cp -a passed_fixtures_stats.json docs/ildottorpalinsesto/passed_fixtures_stats.json 2>/dev/null || true

### REBUILD_FROM_REGISTRY_V1
# Rigenera sempre output PASSA+SUMMARY+DOCS dal registro (zero API) + Telegram per match
python3 tools/rebuild_from_registry.py || true

# Pubblica JSON per GitHub Pages
./publish_docs.sh
