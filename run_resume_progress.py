import json, time, sys
from pathlib import Path
from datetime import datetime

FIXT = Path("league_fixtures.json")
REG  = Path("stats_checked.json")

if not FIXT.exists():
    sys.exit("ERRORE: league_fixtures.json non trovato in ~/BangladinoRobot")

fixtures = json.loads(FIXT.read_text(encoding="utf-8"))
registry = json.loads(REG.read_text(encoding="utf-8")) if REG.exists() else {}

def get_fixture_id(x):
    # supporta strutture diverse
    if isinstance(x, dict):
        if "fixture_id" in x: return int(x["fixture_id"])
        if "fixture" in x and isinstance(x["fixture"], dict) and "id" in x["fixture"]:
            return int(x["fixture"]["id"])
        if "id" in x and str(x["id"]).isdigit():
            return int(x["id"])
    return None

# todo = solo quelli NON già nel registry
done_ids = set(str(k) for k in registry.keys())
todo = []
for x in fixtures:
    fid = get_fixture_id(x)
    if fid is None: 
        continue
    if str(fid) in done_ids:
        continue
    todo.append(fid)

total = len(todo)
print(f"RESUME: già in registry = {len(done_ids)} | da fare ora = {total}")

# import qui per evitare crash se FIXT manca
from stats_batch_apifootball import analyze_fixture_with_registry

for i, fid in enumerate(todo, 1):
    print(f"\n[{i} su {total}] 🔍 fixture {fid}  ({datetime.utcnow().isoformat(timespec='seconds')}Z)")
    try:
        registry = analyze_fixture_with_registry(fid, registry)
    except Exception as e:
        print(f"⚠️ ERRORE fixture {fid}: {e}")
        time.sleep(3)
        continue

    # salva ogni volta (sicuro, ma un filo più lento)
    REG.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")

print("\n✅ FINITO")
