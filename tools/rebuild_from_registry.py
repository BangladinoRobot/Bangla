import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

# --- config telegram (usa le funzioni già presenti nel repo) ---
def tg_send(msg: str):
    try:
        from telegram_utils import send_telegram_message
        send_telegram_message(msg)
    except Exception:
        pass

ROOT = Path(".")
REGISTRY = ROOT / "stats_checked.json"
SUMMARY  = ROOT / "stats_summary.json"
PASSED   = ROOT / "passed_fixtures_stats.json"
DOCS_DIR = ROOT / "docs" / "ildottorpalinsesto"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

NOTIFIED = ROOT / "notified_passed.json"  # evita spam duplicati

def dt(s):
    if not s: return None
    if isinstance(s, str) and s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except Exception:
        return None

def load_json(path: Path, default):
    try:
        txt = path.read_text(encoding="utf-8", errors="ignore").strip()
        if not txt:
            return default
        return json.loads(txt)
    except Exception:
        return default

def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def main(days_ahead=6):
    sc = load_json(REGISTRY, {})
    vals = list(sc.values())

    now = datetime.now(timezone.utc)
    today = now.date()
    end = (now + timedelta(days=days_ahead)).date()

    passed_all = [v for v in vals if v.get("passes_7_on_14") is True]

    passed_window = []
    for v in passed_all:
        t = dt(v.get("fixture_date"))
        if not t:
            continue
        if not (today <= t.date() <= end):
            continue
        passed_window.append(v)

    passed_window.sort(key=lambda x: dt(x.get("fixture_date")) or now)

    out = []
    for v in passed_window:
        out.append({
            "fixture_id": v.get("fixture_id"),
            "fixture_date": v.get("fixture_date"),
            "league_country": v.get("league_country"),
            "league_name": v.get("league_name"),
            "league_id": v.get("league_id"),
            "home_name": v.get("home_name"),
            "away_name": v.get("away_name"),
            "total_0_0_1_1": v.get("total_0_0_1_1"),
            "total_games": v.get("total_games"),
        })

    # salva output (root + docs)
    save_json(PASSED, out)
    save_json(DOCS_DIR / "passed_fixtures_stats.json", out)

    # aggiorna summary (senza rompere le altre chiavi)
    summary = load_json(SUMMARY, {})
    summary["stats_pass_count_all"] = len(passed_all)
    summary["stats_pass_count_window"] = len(out)
    summary["stats_pass_range_days"] = days_ahead
    summary["updated_at_utc"] = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
    save_json(SUMMARY, summary)
    save_json(DOCS_DIR / "stats_summary.json", summary)

    # copia registry in docs (dashboard)
    save_json(DOCS_DIR / "stats_checked.json", sc)

    print("OK: rebuilt passed_fixtures_stats.json =", len(out), "(window)")
    print("OK: summary updated. PASSA all=", len(passed_all))

    # Telegram: invia 1 msg per match nuovo (no duplicati nello stesso giorno)
    notified = load_json(NOTIFIED, {"date": str(today), "ids": []})
    if notified.get("date") != str(today):
        notified = {"date": str(today), "ids": []}
    sent_ids = set(notified.get("ids") or [])

    new_msgs = 0
    for v in out:
        fid = v["fixture_id"]
        if fid in sent_ids:
            continue
        msg = (
            "✅ PASSA 7/14 (0-0/1-1)\n"
            f"🏟 {v['league_country']} – {v['league_name']}\n"
            f"⚽ {v['home_name']} vs {v['away_name']}\n"
            f"📈 {v['total_0_0_1_1']}/{v['total_games']} | 🆔 {fid}\n"
            f"🕒 {v['fixture_date']}\n"
            "🔗 Dashboard: https://bangladinorobot.github.io/Bangla/ildottorpalinsesto/"
        )
        tg_send(msg)
        sent_ids.add(fid)
        new_msgs += 1

    notified["ids"] = sorted(sent_ids)
    save_json(NOTIFIED, notified)
    print("OK: telegram sent new =", new_msgs)

if __name__ == "__main__":
    main()
