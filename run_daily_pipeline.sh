#!/bin/bash
cd /home/pi/BangladinoRobot || exit 1
source venv/bin/activate

run_once() {
  python3 screen_league_fixtures.py || return 1
  python3 run_stats_on_league_fixtures.py || return 1
  python3 odds_layer_theoddsapi.py || return 1
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
