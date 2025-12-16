import json
import os
from datetime import datetime
from stats_batch_apifootball import (
    load_registry,
    save_registry,
    analyze_fixture_with_registry,
    prune_registry,
)

FIXTURES_FILE = "league_fixtures.json"

def load_fixtures():
    """Carica la lista di partite di campionato dal file JSON creato dallo screening."""
    if not os.path.exists(FIXTURES_FILE):
        print(f"File {FIXTURES_FILE} non trovato. Esegui prima screen_league_fixtures.py.")
        return []

    try:
        with open(FIXTURES_FILE, "r", encoding="utf-8") as f:
            fixtures = json.load(f)


# TEAM_DEDUPE_ENABLED: 1
# Se una squadra appare più volte nel palinsesto caricato, analizziamo SOLO la sua prima partita (la più vicina nel tempo).
# Le partite successive con una delle due squadre già viste vengono SKIPPATE (non analizzate e non salvate nel registro).
def _safe_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None

def _dedupe_by_team(fixtures):
    fixtures_sorted = sorted(fixtures, key=lambda x: (_safe_dt(x.get("date")) or datetime.max))
    seen = set()
    out = []
    for fx in fixtures_sorted:
        home = fx.get("home_id") or fx.get("home_name")
        away = fx.get("away_id") or fx.get("away_name")
        # se mancano i dati, non deduplichiamo (evitiamo errori)
        if not home or not away:
            out.append(fx)
            continue
        if home in seen or away in seen:
            continue
        out.append(fx)
        seen.add(home); seen.add(away)
    return out

fixtures = _dedupe_by_team(fixtures)

            if not isinstance(fixtures, list):
                print(f"Contenuto di {FIXTURES_FILE} non valido (non è una lista).")
                return []
            return fixtures
    except Exception as e:
        print(f"Errore nel leggere {FIXTURES_FILE}: {e}")
        return []

def parse_iso_datetime(s):
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None

def is_next_for_both_teams(target, all_fixtures):
    """
    Ritorna True se, nell'elenco all_fixtures (oggi + 3 giorni),
    la partita 'target' è la prima gara futura sia per la squadra di casa
    che per quella in trasferta.
    """
    target_date = parse_iso_datetime(target.get("date"))
    if not target_date:
        # se non riusciamo a leggere la data, non blocchiamo l'analisi
        return True

    home_id = target.get("home_id")
    away_id = target.get("away_id")

    # se non abbiamo gli id delle squadre (vecchi dati), non blocchiamo
    if not home_id or not away_id:
        return True

    for other in all_fixtures:
        if other is target:
            continue

        other_date = parse_iso_datetime(other.get("date"))
        if not other_date:
            continue

        # ci interessano solo partite PRIMA di quella target
        if other_date >= target_date:
            continue

        o_home = other.get("home_id")
        o_away = other.get("away_id")

        # se una delle due squadre gioca prima di questa partita, questa NON è la prossima
        if o_home in (home_id, away_id) or o_away in (home_id, away_id):
            return False

    return True

def main():
    # 1) Carichiamo le partite di campionato trovate dallo screening
    fixtures = load_fixtures()
    print(f"Partite di campionato da analizzare (da {FIXTURES_FILE}): {len(fixtures)}")

    if not fixtures:
        print("Nessuna partita di campionato trovata in league_fixtures.json. Esco.")
        return

    # 2) Carichiamo il registro 7x7
    registry = load_registry()
    print(f"Partite già presenti nel registro: {len(registry)}")
    registry = prune_registry(registry, keep_days=180)

    passed_fixtures = []

    # 3) Cicliamo sulle partite di campionato (già ordinate per priorità nel file JSON)
    for item in fixtures:
        fixture_id = item["fixture_id"]
        key = str(fixture_id)

        # Refinement: analizza solo se questa è la PROSSIMA partita
        # per entrambe le squadre, nel palinsesto di oggi + 3 giorni.
        if not is_next_for_both_teams(item, fixtures):
            print(f"[SKIP] Salto fixture {fixture_id}: non è la prossima partita per una delle due squadre.")
            continue

        try:
            registry = analyze_fixture_with_registry(fixture_id, registry)
        except ValueError as e:
            # Es. "Nessuna fixture trovata per id 1485777"
            print(f"⚠️ {e}. Salto questa fixture.")
            continue

        info = registry.get(key)
        if not info:
            continue

        if info.get("passes_rule"):
            passed_fixtures.append({
                "fixture_id": fixture_id,
                "date": item.get("date"),
                "country": item.get("country"),
                "league_name": item.get("league_name"),
                "home_name": item.get("home_name"),
                "away_name": item.get("away_name"),
                "total_00_11": info.get("total_00_11"),
            })

    # 4) Salviamo il registro aggiornato
    save_registry(registry)

    # 5) Stampiamo le partite che PASSANO la regola 7 su 14
    print("\n==============================")
    print("Partite che PASSANO la regola 7 su 14 (0–0 / 1–1):", len(passed_fixtures))

    for pf in passed_fixtures:
        print(
            f"{pf['date']} | {pf['fixture_id']} | "
            f"{pf['country']} - {pf['league_name']}: "
            f"{pf['home_name']} vs {pf['away_name']} "
            f"(totale {pf['total_00_11']} su 14)"
        )

    # 6) Salviamo le partite che passano 7/14 in un JSON dedicato
    with open("passed_fixtures_stats.json", "w", encoding="utf-8") as f_out:
        json.dump(passed_fixtures, f_out, ensure_ascii=False, indent=2)

    print(f"\nSalvate {len(passed_fixtures)} partite che passano 7/14 in passed_fixtures_stats.json")

    # 7) Salviamo un riepilogo statistico delle partite analizzate
    total_fixtures = len(fixtures)
    total_passed = len(passed_fixtures)

    if fixtures:
        # Gestiamo sia la vecchia struttura (date/country)
        # sia la nuova (fixture_date/league_country)
        dates = []
        for f in fixtures:
            d = f.get("date") or f.get("fixture_date")
            if d:
                dates.append(d)
        date_min = min(dates) if dates else None
        date_max = max(dates) if dates else None

        leagues_set = set()
        for f in fixtures:
            country = f.get("country") or f.get("league_country") or "N/A"
            league_name = f.get("league_name") or "N/A"
            leagues_set.add(f"{country} - {league_name}")
        leagues = sorted(leagues_set)
    else:
        date_min = None
        date_max = None
        leagues = []

    stats_summary = {
        "total_fixtures": total_fixtures,
        "total_passed": total_passed,
        "date_min": date_min,
        "date_max": date_max,
        "leagues": leagues,
    }

    with open("stats_summary.json", "w", encoding="utf-8") as f_sum:
        json.dump(stats_summary, f_sum, ensure_ascii=False, indent=2)

    print(f"Salvato riepilogo statistico in stats_summary.json")

if __name__ == "__main__":
    main()
