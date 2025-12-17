#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs" / "ildottorpalinsesto"
DATA = DOCS / "data"

STATS_CHECKED = ROOT / "stats_checked.json"
ODDS_RESULTS = ROOT / "odds_results.json"
STATS_SUMMARY = ROOT / "stats_summary.json"

def _load_json(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default

def _parse_dt(s: str):
    if not s:
        return None
    try:
        # created_at è senza tz: trattiamolo come UTC
        if len(s) == 19 and "T" in s:
            return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None

def _utc_today():
    return datetime.now(timezone.utc).date()

def main():
    DATA.mkdir(parents=True, exist_ok=True)

    stats_checked = _load_json(STATS_CHECKED, {})
    odds_results = _load_json(ODDS_RESULTS, [])
    stats_summary = _load_json(STATS_SUMMARY, {})

    now_utc = datetime.now(timezone.utc)
    today_utc = _utc_today()

    # indicizza odds per fixture_id
    odds_by_fixture = {}
    if isinstance(odds_results, list):
        for r in odds_results:
            try:
                fid = str(r.get("fixture_id"))
                odds_by_fixture[fid] = r
            except Exception:
                continue

    # raccogli filter1 (passa 7/14)
    f1_all = []
    f1_today = []
    for fid, e in (stats_checked or {}).items():
        if not isinstance(e, dict):
            continue
        if not e.get("passes_7_on_14"):
            continue

        fx_dt = _parse_dt(e.get("fixture_date"))  # di solito ha offset
        cr_dt = _parse_dt(e.get("created_at"))

        item = {
            "fixture_id": int(e.get("fixture_id") or fid),
            "fixture_date": e.get("fixture_date"),
            "league_country": e.get("league_country"),
            "league_name": e.get("league_name"),
            "home_name": e.get("home_name"),
            "away_name": e.get("away_name"),
            "home_0_0_1_1": e.get("home_0_0_1_1"),
            "away_0_0_1_1": e.get("away_0_0_1_1"),
            "total_0_0_1_1": e.get("total_0_0_1_1"),
            # predisposizione split (da riempire quando aggiorniamo stats_batch)
            "home_00": e.get("home_00"),
            "home_11": e.get("home_11"),
            "away_00": e.get("away_00"),
            "away_11": e.get("away_11"),
            "created_at": e.get("created_at"),
        }

        f1_all.append(item)

        # "ultima analisi": tutto ciò creato oggi (UTC)
        if cr_dt and cr_dt.date() == today_utc:
            f1_today.append(item)

    # filter2 = AUTO_OK da The Odds API (quote ok)
    f2_all = []
    f2_today = []
    if isinstance(odds_results, list):
        for r in odds_results:
            if (r or {}).get("status") != "AUTO_OK":
                continue
            try:
                fid = int(r.get("fixture_id"))
            except Exception:
                continue

            # prova ad agganciare anche i dati del filtro1 se disponibili
            e = stats_checked.get(str(fid), {}) if isinstance(stats_checked, dict) else {}
            item = {
                "fixture_id": fid,
                "fixture_date": e.get("fixture_date"),
                "league_country": r.get("country") or e.get("league_country"),
                "league_name": r.get("league_name") or e.get("league_name"),
                "home_name": r.get("home_name") or e.get("home_name"),
                "away_name": r.get("away_name") or e.get("away_name"),
                "total_0_0_1_1": r.get("total_00_11") or e.get("total_0_0_1_1"),
                "draw_price": r.get("draw_price"),
                "under25_price": r.get("under25_price"),
                "bookmaker": "bet365",
            }
            f2_all.append(item)

            # se la fixture è nella run odierna (created_at oggi) la consideriamo "ultima analisi"
            cr_dt = _parse_dt((e or {}).get("created_at"))
            if cr_dt and cr_dt.date() == today_utc:
                f2_today.append(item)

    # futuro vs passato (per calendario/archivio)
    def is_future(it):
        d = _parse_dt(it.get("fixture_date"))
        return (d is None) or (d >= now_utc)

    cal_upcoming = [it for it in f1_all if is_future(it)]

    # meta
    meta = {
        "generated_at_utc": now_utc.isoformat(timespec="seconds"),
        "today_utc": str(today_utc),
        "total_fixtures_analyzed": int((stats_summary or {}).get("total_fixtures") or 0),
        "leagues_count": int(len((stats_summary or {}).get("leagues") or [])),
        "filter1_count_today": len(f1_today),
        "filter2_count_today": len(f2_today),
        "filter1_count_upcoming": len(cal_upcoming),
    }

    (DATA / "run_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "filter1_today.json").write_text(json.dumps(sorted(f1_today, key=lambda x: x.get("fixture_date") or ""), ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "filter2_today.json").write_text(json.dumps(sorted(f2_today, key=lambda x: x.get("fixture_date") or ""), ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "calendar_upcoming.json").write_text(json.dumps(sorted(cal_upcoming, key=lambda x: x.get("fixture_date") or ""), ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "archive_filter1.json").write_text(json.dumps(sorted(f1_all, key=lambda x: x.get("fixture_date") or ""), ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "archive_filter2.json").write_text(json.dumps(sorted(f2_all, key=lambda x: x.get("fixture_date") or ""), ensure_ascii=False, indent=2), encoding="utf-8")

    print("OK: dashboard JSON generati in", DATA)

if __name__ == "__main__":
    main()
