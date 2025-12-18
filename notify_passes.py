import json
import sys
from pathlib import Path
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Europe/Rome")
except Exception:
    TZ = None

# --- input/output ---
STATS_CHECKED = Path("stats_checked.json")
STATS_SUMMARY = Path("stats_summary.json")
PASSED_FILE = Path("passed_fixtures_stats.json")
PASSED_ARCHIVE = Path("passed_fixtures_archive.json")

DOCS_DIR = Path("docs/ildottorpalinsesto")

DRY_RUN = ("--dry-run" in sys.argv)

def _parse_dt(s: str):
    if not s:
        return None
    try:
        # normalize Z
        if isinstance(s, str) and s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None

def _now():
    return datetime.now(TZ) if TZ else datetime.now()

def _to_local_str(dt: datetime):
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if TZ:
        dt = dt.astimezone(TZ)
    return dt.strftime("%d/%m/%Y %H:%M")

def load_json(p: Path, default):
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return default

def save_json(p: Path, data):
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def telegram_available():
    try:
        import config
        # NON stampo il token, controllo solo presenza
        token = getattr(config, "TELEGRAM_BOT_TOKEN", None) or getattr(config, "TELEGRAM_TOKEN", None)
        chat = getattr(config, "TELEGRAM_CHAT_ID", None) or getattr(config, "TELEGRAM_GROUP_ID", None)
        return bool(token and chat)
    except Exception:
        return False

def send_telegram(text: str):
    if DRY_RUN:
        print("[DRY RUN] Telegram:\n", text)
        return
    try:
        from telegram_utils import send_telegram_message
        send_telegram_message(text)
    except Exception as e:
        print("WARN: invio Telegram fallito:", repr(e))

def main():
    if not STATS_CHECKED.exists():
        print("ERRORE: stats_checked.json non trovato")
        return 2

    stats = load_json(STATS_CHECKED, {})
    vals = list(stats.values())

    # counts base
    leagues = {(v.get("league_id"), v.get("league_name"), v.get("league_country")) for v in vals if v.get("league_id")}
    analyzed_count = len(vals)
    leagues_count = len(leagues)

    # PASSA 7/14
    passed_all = [v for v in vals if v.get("passes_7_on_14") is True]

    # SOLO future/upcoming
    now = _now()
    passed_upcoming = []
    for v in passed_all:
        dt = _parse_dt(v.get("fixture_date"))
        if dt is None:
            continue
        # confronto in locale se possibile
        if TZ and dt.tzinfo:
            dt_loc = dt.astimezone(TZ)
        else:
            dt_loc = dt
        if dt_loc >= now:
            passed_upcoming.append(v)

    # ordina per data
    def key_dt(v):
        dt = _parse_dt(v.get("fixture_date"))
        return dt or datetime.max.replace(tzinfo=timezone.utc)
    passed_upcoming.sort(key=key_dt)

    # aggiorna summary coerente col registro
    summary = load_json(STATS_SUMMARY, {})
    summary["generated_at_local"] = _now().strftime("%Y-%m-%d %H:%M:%S")
    summary["matches_analyzed"] = analyzed_count
    summary["leagues_analyzed"] = leagues_count
    summary["passes_7_on_14"] = len(passed_upcoming)
    save_json(STATS_SUMMARY, summary)

    # esporta JSON per dashboard
    save_json(PASSED_FILE, passed_upcoming)
    save_json(PASSED_ARCHIVE, passed_all)

    # TELEGRAM: invia SOLO nuove partite non notificate
    can_tg = telegram_available()
    sent = 0

    for v in passed_upcoming:
        fid = str(v.get("fixture_id") or "")
        if not fid:
            continue

        # flag anti-duplicato dentro stats_checked.json
        if v.get("telegram_notified_at"):
            continue

        league = f"{v.get('league_country','')} - {v.get('league_name','')}".strip(" -")
        match = f"{v.get('home_name','?')} vs {v.get('away_name','?')}"
        ratio = f"{v.get('total_0_0_1_1','?')}/{v.get('total_games','?')}"
        h = f"{v.get('home_0_0_1_1','?')}/{v.get('home_matches_analyzed','?')}"
        a = f"{v.get('away_0_0_1_1','?')}/{v.get('away_matches_analyzed','?')}"
        dt = _parse_dt(v.get("fixture_date"))
        when = _to_local_str(dt)

        text = (
            "✅ PASSA 7/14 (0-0 o 1-1)\n"
            f"🏆 {league}\n"
            f"⚽ {match}\n"
            f"🗓 {when}\n"
            f"📊 Totale: {ratio}  |  Casa: {h}  |  Trasferta: {a}\n"
            f"🆔 fixture_id: {fid}"
        )

        if can_tg:
            send_telegram(text)
        else:
            # se non configurato, almeno lo stampa
            print("INFO: Telegram non configurato, stampo:\n", text)

        # marca come notificata
        v["telegram_notified_at"] = _now().strftime("%Y-%m-%d %H:%M:%S")
        sent += 1

    # salva indietro stats_checked con i flag telegram
    # ricostruisco per fixture_id
    out = {str(v.get("fixture_id")): v for v in vals if v.get("fixture_id") is not None}
    save_json(STATS_CHECKED, out)

    # copia in docs per GitHub Pages
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    save_json(DOCS_DIR / "stats_summary.json", summary)
    save_json(DOCS_DIR / "passed_fixtures_stats.json", passed_upcoming)
    save_json(DOCS_DIR / "passed_fixtures_archive.json", passed_all)

    print(f"OK: summary={summary.get('passes_7_on_14',0)} passate (upcoming). Telegram nuove inviate: {sent}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
