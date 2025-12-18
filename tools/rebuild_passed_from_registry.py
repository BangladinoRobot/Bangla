#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(".")
DOCS = ROOT / "docs" / "ildottorpalinsesto"

def load_json(p: Path, default):
    try:
        t = p.read_text(encoding="utf-8", errors="ignore").strip()
        return json.loads(t) if t else default
    except Exception:
        return default

def parse_dt(s):
    if not s:
        return None
    if isinstance(s, str) and s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except Exception:
        return None

def write_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

# sorgente: root stats_checked, fallback docs
src = ROOT / "stats_checked.json"
if not src.exists():
    src = DOCS / "stats_checked.json"

sc = load_json(src, {})
vals = list(sc.values()) if isinstance(sc, dict) else []
passed_all = [v for v in vals if v.get("passes_7_on_14") is True]

now = datetime.now(timezone.utc)
today = now.date()
end = (now + timedelta(days=6)).date()

passed_window = []
for v in passed_all:
    t = parse_dt(v.get("fixture_date"))
    if not t:
        continue
    if today <= t.date() <= end:
        passed_window.append(v)

passed_all_sorted = sorted(passed_all, key=lambda x: parse_dt(x.get("fixture_date")) or now)
passed_window_sorted = sorted(passed_window, key=lambda x: parse_dt(x.get("fixture_date")) or now)

# scrivo root + docs
write_json(ROOT / "passed_fixtures_stats.json", passed_window_sorted)
write_json(DOCS / "passed_fixtures_stats.json", passed_window_sorted)

# (opzionale) salvo anche “all”
write_json(ROOT / "passed_fixtures_stats_all.json", passed_all_sorted)
write_json(DOCS / "passed_fixtures_stats_all.json", passed_all_sorted)

# aggiorno stats_summary (root+docs) senza rompere campi già presenti
def bump_summary(path: Path):
    ss = load_json(path, {})
    if not isinstance(ss, dict):
        ss = {}
    ss["generated_at_utc"] = now.isoformat(timespec="seconds")
    ss["stats_pass_count_all"] = len(passed_all_sorted)
    ss["stats_pass_count_window"] = len(passed_window_sorted)
    write_json(path, ss)

bump_summary(ROOT / "stats_summary.json")
bump_summary(DOCS / "stats_summary.json")

print("OK rebuild_passed_from_registry")
print("PASSA all:", len(passed_all_sorted))
print("PASSA window (oggi..+6gg):", len(passed_window_sorted))
