#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "ildottorpalinsesto"
DATA = DOCS / "data"
DATA.mkdir(parents=True, exist_ok=True)

FIN = {"FT", "AET", "PEN"}

def _read_json(p: Path, default):
    try:
        if not p.exists():
            return default
        txt = p.read_text(encoding="utf-8", errors="ignore").strip()
        if not txt:
            return default
        return json.loads(txt)
    except Exception:
        return default

def _to_int(v):
    try:
        return int(v)
    except Exception:
        return None

def _parse_dt(s):
    if not s:
        return None
    s = str(s).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

def _as_bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        x = v.strip().lower()
        if x in {"true","yes","y","1","ok"}:
            return True
        if x in {"false","no","n","0"}:
            return False
    return False

def _pass1(entry: dict) -> bool:
    for k in ("passes_7_on_14", "passa", "passes", "pass", "passes_filter1"):
        if k in entry:
            return _as_bool(entry.get(k))
    return False

def _total_0_0_1_1(entry: dict) -> int:
    for k in ("total_0_0_1_1", "total", "total_0_0_1_1_last14"):
        v = entry.get(k)
        if isinstance(v, int):
            return v
        iv = _to_int(v)
        if iv is not None:
            return iv
    t00 = _to_int(entry.get("total_0_0")) or 0
    t11 = _to_int(entry.get("total_1_1")) or 0
    return t00 + t11

def _status_short(entry: dict) -> str:
    v = entry.get("fixture_status_short") or entry.get("status_short") or entry.get("status")
    return v.strip() if isinstance(v, str) else ""

def _is_finished(entry: dict) -> bool:
    if entry.get("ft_mark"):
        return True
    return _status_short(entry) in FIN

def _normalize_entry(entry: dict) -> dict:
    return {
        "fixture_id": entry.get("fixture_id"),
        "fixture_date": entry.get("fixture_date"),
        "home_id": entry.get("home_id"),
        "home_name": entry.get("home_name"),
        "away_id": entry.get("away_id"),
        "away_name": entry.get("away_name"),
        "league_id": entry.get("league_id"),
        "league_name": entry.get("league_name"),
        "league_country": entry.get("league_country"),
        "total_0_0_1_1": _total_0_0_1_1(entry),
        "passes_7_on_14": _pass1(entry),
        "ft_mark": entry.get("ft_mark"),
        "ft_score": entry.get("ft_score"),
        "fixture_status_short": entry.get("fixture_status_short") or entry.get("status_short") or entry.get("status"),
    }

def _load_stats_checked() -> dict:
    p1 = DOCS / "stats_checked.json"
    p2 = ROOT / "stats_checked.json"
    data = _read_json(p1, None)
    if isinstance(data, dict) and data:
        return data
    data = _read_json(p2, {})
    return data if isinstance(data, dict) else {}

def _load_odds_results() -> dict:
    candidates = [
        DOCS / "odds_results.json",
        ROOT / "odds_results.json",
        ROOT / "odds_results" / "odds_results.json",
        DOCS / "odds_results" / "odds_results.json",
    ]
    raw = None
    for p in candidates:
        raw = _read_json(p, None)
        if raw is not None:
            break
    if raw is None:
        return {}

    out = {}
    if isinstance(raw, dict):
        if "results" in raw and isinstance(raw["results"], list):
            raw = raw["results"]
        else:
            for k, v in raw.items():
                fid = _to_int(k) or _to_int(v.get("fixture_id") if isinstance(v, dict) else None)
                if fid is not None and isinstance(v, dict):
                    out[fid] = v
            return out

    if isinstance(raw, list):
        for it in raw:
            if not isinstance(it, dict):
                continue
            fid = _to_int(it.get("fixture_id")) or _to_int(it.get("id"))
            if fid is None:
                continue
            out[fid] = it
    return out

def _pass2(od: dict) -> bool:
    if not isinstance(od, dict):
        return False
    for k in ("pass2", "passes_second_filter", "passes_filter2", "second_filter_pass", "pass_second_filter"):
        if k in od:
            return _as_bool(od.get(k))
    return False

def main():
    now = datetime.now(timezone.utc)
    today = now.date()
    window_end = today + timedelta(days=6)

    stats = _load_stats_checked()
    odds_map = _load_odds_results()

    entries = []
    leagues = set()

    for _, e in stats.items():
        if not isinstance(e, dict):
            continue
        ne = _normalize_entry(e)
        if isinstance(ne.get("league_name"), str) and ne["league_name"].strip():
            leagues.add(ne["league_name"].strip())
        entries.append(ne)

    pass1_all = [e for e in entries if e.get("passes_7_on_14")]

    pass1_upcoming, pass1_window, pass1_archive = [], [], []
    for e in pass1_all:
        dt = _parse_dt(e.get("fixture_date"))
        if not dt:
            continue
        d = dt.date()
        if d >= today:
            pass1_upcoming.append(e)
            if d <= window_end:
                pass1_window.append(e)
        else:
            if _is_finished(e) or d < today:
                pass1_archive.append(e)

    pass2_upcoming, pass2_window, pass2_archive = [], [], []
    for e in pass1_all:
        fid = _to_int(e.get("fixture_id"))
        od = odds_map.get(fid, {})
        if not _pass2(od):
            continue
        dt = _parse_dt(e.get("fixture_date"))
        if not dt:
            continue
        d = dt.date()

        e2 = dict(e)
        if isinstance(od, dict):
            for k in ("best_market","best_bookmaker","best_price","best_label","best_odds","market","bookmaker"):
                if k in od and k not in e2:
                    e2[k] = od.get(k)
            e2["pass2"] = True

        if d >= today:
            pass2_upcoming.append(e2)
            if d <= window_end:
                pass2_window.append(e2)
        else:
            if _is_finished(e2) or d < today:
                pass2_archive.append(e2)

    def _sort_key(e):
        dt = _parse_dt(e.get("fixture_date"))
        return dt or datetime(1970,1,1,tzinfo=timezone.utc)

    pass1_upcoming.sort(key=_sort_key)
    pass2_upcoming.sort(key=_sort_key)
    pass1_window.sort(key=_sort_key)
    pass2_window.sort(key=_sort_key)
    pass1_archive.sort(key=_sort_key, reverse=True)
    pass2_archive.sort(key=_sort_key, reverse=True)

    run_meta = {
        "generated_at_utc": now.isoformat(),
        "today_utc": str(today),
        "total_fixtures_analyzed": len(stats),
        "leagues_count": len(leagues),
        "filter1_count_today": len(pass1_window),
        "filter2_count_today": len(pass2_window),
        "filter1_count_upcoming": len(pass1_upcoming),
        "filter2_count_upcoming": len(pass2_upcoming),
    }

    (DATA / "run_meta.json").write_text(json.dumps(run_meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "filter1_today.json").write_text(json.dumps(pass1_window, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "filter2_today.json").write_text(json.dumps(pass2_window, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "filter1_upcoming.json").write_text(json.dumps(pass1_upcoming, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "filter2_upcoming.json").write_text(json.dumps(pass2_upcoming, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "archive_filter1.json").write_text(json.dumps(pass1_archive, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "archive_filter2.json").write_text(json.dumps(pass2_archive, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "calendar_upcoming.json").write_text(json.dumps(pass1_upcoming, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK build_dashboard_data: f1_upcoming={len(pass1_upcoming)} f2_upcoming={len(pass2_upcoming)} a1={len(pass1_archive)} a2={len(pass2_archive)}")

if __name__ == "__main__":
    main()
