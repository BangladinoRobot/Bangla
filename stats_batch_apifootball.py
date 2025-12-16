import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

import requests

from config import API_FOOTBALL_KEY

BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_FOOTBALL_KEY,
}

# Cache in memoria
# Flag limiti piano (per evitare di registrare fixture non analizzate)
PLAN_LIMIT_THIS_FIXTURE = False
PLAN_LIMIT_SKIPPED_FIXTURES = 0
PLAN_LIMIT_FILE = "plan_limit_reached.json"

def _write_plan_limit_flag(context: str = "", detail: str = "", inc_skip: bool = False) -> None:
    global PLAN_LIMIT_SKIPPED_FIXTURES
    try:
        if inc_skip:
            PLAN_LIMIT_SKIPPED_FIXTURES += 1
        payload = {
            "ts_utc": datetime.datetime.utcnow().isoformat(timespec="seconds"),
            "context": context,
            "detail": detail,
            "skipped_fixtures": PLAN_LIMIT_SKIPPED_FIXTURES,
        }
        Path(PLAN_LIMIT_FILE).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

LEAGUE_SEASON_CACHE: Dict[Tuple[int, Optional[int]], Optional[int]] = {}
PLAN_LIMIT_SKIPPED_FIXTURES: list[int] = []  # SKIP_PLAN_LIMIT_NO_REGISTRY
TEAM_SEASON_FIXTURES_CACHE: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}

LEAGUE_FIXTURES_INDEX: Dict[int, Dict[str, Any]] = {}
_LEAGUE_FIXTURES_LOADED = False


# ------------------------------------------------------------
# Utility generiche
# ------------------------------------------------------------

def _parse_datetime(value: str) -> Optional[datetime]:
    """Parsa una stringa ISO (con o senza timezone) in datetime."""
    if not isinstance(value, str):
        return None
    # Proviamo con ISO standard
    try:
        s = value.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        pass

    # Alcuni formati più semplici
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            continue

    return None


def _parse_fixture_datetime(value: str) -> Optional[datetime]:
    """Parsa la data fixture in datetime (con timezone se presente)."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return _parse_datetime(value)


def _api_get(path: str, params: Dict[str, Any], context: str = "", max_retries: int = 3) -> Optional[Dict[str, Any]]:
    """Wrapper per le chiamate API-Football con gestione errori e rate limit."""
    url = f"{BASE_URL}{path}"

    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=20)
        except Exception as e:
            print(f"⚠️ Errore di rete chiamando {path} ({context}): {e}")
            return None

        if resp.status_code != 200:
            print(f"⚠️ Risposta HTTP {resp.status_code} per {path} ({context}).")
            return None

        try:
            data = resp.json()
        except Exception as e:
            print(f"⚠️ Errore nel parsing JSON da {path} ({context}): {e}")
            return None

        errors = data.get("errors") or {}

        # Gestione rate limit
        rate_err = errors.get("rateLimit")
        if rate_err:
            wait = 7 * (attempt + 1)
            print(f"⚠️ API-Football rateLimit ({context}): {rate_err}. Riprovo tra {wait} secondi...")
            time.sleep(wait)
            continue

        plan_err = errors.get("plan")
        if plan_err:
            global PLAN_LIMIT_THIS_FIXTURE
            PLAN_LIMIT_THIS_FIXTURE = True
            print(f"⚠️ Limite piano API-Football ({context}): {plan_err}")
            _write_plan_limit_flag(context=context, detail=str(plan_err), inc_skip=False)
            return data

        season_err = errors.get("season")
        if season_err:
            print(f"⚠️ Errore season API-Football ({context}): {season_err}")
            return data

        return data

    print(f"⚠️ Troppi tentativi falliti per {path} ({context}).")
    return None


# ------------------------------------------------------------
# Gestione registro su file (stats_checked.json)
# ------------------------------------------------------------

def load_registry(path: str = "stats_checked.json") -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        return {}
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        print(f"⚠️ Impossibile decodificare {path}. Uso registro vuoto.")
        return {}


def save_registry(registry: Dict[str, Any], path: str = "stats_checked.json") -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)


def prune_registry(registry: Dict[str, Any], keep_days: int = 180) -> Dict[str, Any]:
    """Rimuove dal registro le analisi più vecchie di keep_days (in giorni)."""
    if not registry:
        print("Pulizia registro: rimossi 0 elementi vecchi, rimasti 0.")
        return {}

    cutoff = datetime.utcnow() - timedelta(days=keep_days)
    new_reg: Dict[str, Any] = {}

    for fixture_id, info in registry.items():
        created_at = info.get("created_at")
        dt = _parse_datetime(created_at) if created_at else None
        # Se non riesco a parsa la data, tengo l'elemento per sicurezza
        if dt is None or dt >= cutoff:
            new_reg[fixture_id] = info

    removed = len(registry) - len(new_reg)
    print(f"Pulizia registro: rimossi {removed} elementi vecchi, rimasti {len(new_reg)}.")
    return new_reg


# ------------------------------------------------------------
# Lettura fixture da league_fixtures.json (invece che dall'API)
# ------------------------------------------------------------

def _ensure_league_fixtures_loaded(path: str = "league_fixtures.json") -> None:
    """Carica league_fixtures.json in un indice per fixture_id."""
    global LEAGUE_FIXTURES_INDEX, _LEAGUE_FIXTURES_LOADED
    if _LEAGUE_FIXTURES_LOADED:
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            fixtures = json.load(f)
    except FileNotFoundError:
        print(f"⚠️ File {path} non trovato. Alcune funzioni potrebbero non funzionare.")
        LEAGUE_FIXTURES_INDEX = {}
        _LEAGUE_FIXTURES_LOADED = True
        return
    except json.JSONDecodeError:
        print(f"⚠️ Impossibile leggere {path} (JSON non valido).")
        LEAGUE_FIXTURES_INDEX = {}
        _LEAGUE_FIXTURES_LOADED = True
        return

    index: Dict[int, Dict[str, Any]] = {}
    for f in fixtures:
        fid = f.get("fixture_id")
        try:
            fid_int = int(fid)
        except Exception:
            continue
        index[fid_int] = f

    LEAGUE_FIXTURES_INDEX = index
    _LEAGUE_FIXTURES_LOADED = True


def get_fixture(fixture_id: int) -> Optional[Dict[str, Any]]:
    """
    Restituisce le info della fixture dal file league_fixtures.json.

    Prima usavamo l'endpoint /fixtures?id=..., ma col piano free / limiti sulle date
    molte chiamate tornavano vuote. Ora ci basiamo sul file che hai già salvato.
    """
    _ensure_league_fixtures_loaded()
    try:
        fid_int = int(fixture_id)
    except Exception:
        return None

    fixture = LEAGUE_FIXTURES_INDEX.get(fid_int)
    if not fixture:
        print(f"⚠️ Nessuna fixture trovata per id {fixture_id} in league_fixtures.json.")
    return fixture


# ------------------------------------------------------------
# Stagione (season) per league
# ------------------------------------------------------------

def get_league_season(league_id: int, fixture_date_iso: str) -> Optional[int]:
    """
    Recupera l'anno di 'season' per una league, in base alla data della fixture.

    Usa /leagues?id=LEAGUE_ID e sceglie la season il cui intervallo start-end
    contiene la data della fixture, altrimenti ripiega sulla season corrente
    o sull'ultima in lista.
    """
    try:
        league_id_int = int(league_id)
    except Exception:
        return None

    fixture_dt = _parse_fixture_datetime(fixture_date_iso)
    year_key = fixture_dt.year if fixture_dt else None
    cache_key = (league_id_int, year_key)

    if cache_key in LEAGUE_SEASON_CACHE:
        return LEAGUE_SEASON_CACHE[cache_key]

    data = _api_get("/leagues", {"id": league_id_int}, context=f"league {league_id_int}")
    # Se il piano NON permette questa season o c'è errore season: non considerare la fixture analizzata
    errs = (data or {}).get('errors') or {}
    if errs.get('plan') or errs.get('season'):
        return None
    if not data or not data.get("response"):
        print(f"⚠️ Nessuna informazione di league per id {league_id_int}.")
        LEAGUE_SEASON_CACHE[cache_key] = None
        return None

    league_info = data["response"][0]
    seasons = league_info.get("seasons") or []
    if not seasons:
        LEAGUE_SEASON_CACHE[cache_key] = None
        return None

    target_date = fixture_dt.date() if fixture_dt else None
    chosen = None

    # 1) Proviamo a trovare la season il cui intervallo contiene la data della fixture
    if target_date:
        for s in seasons:
            start = s.get("start")
            end = s.get("end")
            try:
                sd = datetime.fromisoformat(start[:10]).date() if start else None
                ed = datetime.fromisoformat(end[:10]).date() if end else None
            except Exception:
                sd = ed = None
            if sd and ed and sd <= target_date <= ed:
                chosen = s
                break

    # 2) Se non trovata, usiamo la season corrente
    if not chosen:
        for s in seasons:
            if s.get("current"):
                chosen = s
                break

    # 3) Altrimenti l'ultima season disponibile
    if not chosen:
        chosen = seasons[-1]

    year = chosen.get("year")
    LEAGUE_SEASON_CACHE[cache_key] = year
    return year


# ------------------------------------------------------------
# Ultime partite di una squadra (team, season, status=FT)
# ------------------------------------------------------------

def get_team_finished_fixtures(team_id: int, season_year: int) -> List[Dict[str, Any]]:
    """
    Scarica tutte le partite 'finished' di una squadra in una stagione.

    Usiamo /fixtures?team=TEAM&season=YEAR&status=FT
    e teniamo il risultato in cache (TEAM_SEASON_FIXTURES_CACHE).
    """
    try:
        team_id_int = int(team_id)
        season_int = int(season_year)
    except Exception:
        return []

    key = (team_id_int, season_int)
    if key in TEAM_SEASON_FIXTURES_CACHE:
        return TEAM_SEASON_FIXTURES_CACHE[key]

    params = {
        "team": team_id_int,
        "season": season_int,
        "status": "FT",
    }

    data = _api_get("/fixtures", params, context=f"team {team_id_int}, season {season_int}")
    if (data.get("errors") or {}).get("plan"):
        return None

    if not data:
        TEAM_SEASON_FIXTURES_CACHE[key] = []
        return []

    response = data.get("response") or []
    TEAM_SEASON_FIXTURES_CACHE[key] = response
    return response


def get_last_matches(team_id: int, league_id: int, fixture_date_iso: str, max_matches: int = 7) -> List[Dict[str, Any]]:
    """
    Restituisce le ultime max_matches partite finite di team_id
    prima della data della fixture, usando season corretta.
    """
    season_year = get_league_season(league_id, fixture_date_iso)
    if not season_year:
        return []
    # se non riesco a recuperare season -> skip (non registrare)
    if not season_year:
        return None

    fixtures = get_team_finished_fixtures(team_id, season_year)
    if fixtures is None:
        return None
    if not fixtures:
        return []

    target_dt = _parse_fixture_datetime(fixture_date_iso)

    # Se non riesco a parsa la data della fixture, ordino semplicemente per data desc
    if not target_dt:
        fixtures_sorted = sorted(
            fixtures,
            key=lambda m: _parse_fixture_datetime(m.get("fixture", {}).get("date")),
            reverse=True,
        )
        return fixtures_sorted[:max_matches]

    past: List[Dict[str, Any]] = []
    for m in fixtures:
        f_info = m.get("fixture") or {}
        dt = _parse_fixture_datetime(f_info.get("date"))
        if dt and dt < target_dt:
            past.append(m)

    past.sort(
        key=lambda m: _parse_fixture_datetime(m.get("fixture", {}).get("date")),
        reverse=True,
    )
    return past[:max_matches]


def count_0_0_1_1(matches: List[Dict[str, Any]]) -> int:
    """Conta quante partite hanno risultato esatto 0–0 o 1–1."""
    count = 0
    for m in matches:
        goals = m.get("goals") or {}
        home_goals = goals.get("home")
        away_goals = goals.get("away")
        if home_goals is None or away_goals is None:
            continue
        if (home_goals, away_goals) in [(0, 0), (1, 1)]:
            count += 1
    return count


# ------------------------------------------------------------
# Analisi di una singola fixture + aggiornamento registro
# ------------------------------------------------------------

def analyze_fixture_with_registry(fixture_id: int, registry: Dict[str, Any], max_matches: int = 7) -> Dict[str, Any]:
    """
    Analizza una fixture (per id) usando i dati già salvati in league_fixtures.json
    e aggiorna il registro con i risultati della regola 7 su 14.

    L'interfaccia rimane: ritorna il registry aggiornato.
    """
    fixture_id_str = str(fixture_id)

    # Se già analizzata, non rifaccio chiamate API
    if fixture_id_str in registry:
        entry = registry[fixture_id_str]
        total_pairs = entry.get("total_0_0_1_1", 0)
        total_games = entry.get("total_games", 14)
        passes = entry.get("passes_7_on_14", False)
        home_name = entry.get("home_name", "?")
        away_name = entry.get("away_name", "?")
        print(
            f"⚪ Fixture {fixture_id} già analizzata: {home_name} vs {away_name} "
            f"(totale {total_pairs} su {total_games}, passa={passes})"
        )
        return registry

    fixture = get_fixture(fixture_id)
    if not fixture:
        print(f"⚠️ Nessuna fixture trovata per id {fixture_id}. Salto questa fixture.")
        return registry

    home_id = fixture.get("home_id")
    away_id = fixture.get("away_id")
    home_name = fixture.get("home_name")
    away_name = fixture.get("away_name")
    league_id = fixture.get("league_id")
    fixture_date = fixture.get("fixture_date")
    league_name = fixture.get("league_name")
    league_country = fixture.get("league_country")

    print(f"\n🔍 Analizzo fixture id {fixture_id}...")
    print(f"Partita: {home_name} vs {away_name}")
    print(f"Home team id: {home_id}, Away team id: {away_id}")

    # Home team
    print(f"\nRecupero ultime {max_matches} partite del {home_name}...")
    home_matches = get_last_matches(home_id, league_id, fixture_date, max_matches)
    if home_matches is None:
        print("⏭️ SKIP_PLAN_LIMIT: ultime partite HOME non accessibili (limiti piano). Non registro questa fixture.")
        return registry
    print(f"Trovate {len(home_matches)} partite.")
    home_draws = count_0_0_1_1(home_matches)

    # Away team
    print(f"Recupero ultime {max_matches} partite del {away_name}...")
    away_matches = get_last_matches(away_id, league_id, fixture_date, max_matches)
    if away_matches is None:
        print("⏭️ SKIP_PLAN_LIMIT: ultime partite AWAY non accessibili (limiti piano). Non registro questa fixture.")
        return registry
    print(f"Trovate {len(away_matches)} partite.")

    if len(home_matches) < max_matches or len(away_matches) < max_matches:
        print("⚠️ Dati insufficienti (serve 7+7). Non salvo nel registro: la ricontrollerò quando i dati saranno disponibili.")
        return registry

    away_draws = count_0_0_1_1(away_matches)

    total_draws = home_draws + away_draws
    total_games = len(home_matches) + len(away_matches)

    print(f"\n{home_name}: {home_draws} partite 0–0 o 1–1 su {len(home_matches)}")
    print(f"{away_name}: {away_draws} partite 0–0 o 1–1 su {len(away_matches)}")
    print(f"Totale: {total_draws} su {total_games}")

    # Se non ho nessuna partita storica (0 partite totali),
    # NON devo segnare questa fixture nel registro, così verrà rianalizzata
    # quando il piano API permetterà di leggere lo storico.

    if total_games == 0:
        print("⚠️  Nessuna partita storica disponibile (0 su 0). Registro come NO_DATA.")
        entry = {
            "fixture_id": fixture_id,
            "fixture_date": fixture_date,
            "league_id": league_id,
            "league_name": league_name,
            "league_country": league_country,
            "home_id": home_id,
            "home_name": home_name,
            "away_id": away_id,
            "away_name": away_name,
            "home_matches_analyzed": len(home_matches),
            "home_0_0_1_1": home_draws,
            "away_matches_analyzed": len(away_matches),
            "away_0_0_1_1": away_draws,
            "total_0_0_1_1": total_draws,
            "total_games": total_games,
            "passes_7_on_14": False,
            "status": "NO_DATA",
            "created_at": datetime.utcnow().isoformat(timespec="seconds"),
        }
        registry[fixture_id_str] = entry
        return registry

        # Regola: passa se la somma è >= 7 (restiamo fedeli al concetto 7 su 14)
    passes = total_draws >= 7
    if passes:
        print("✅ La partita PASSA la regola 7 su 14.")
    else:
        print("❌ La partita NON passa la regola 7 su 14.")

    entry = {
        "fixture_id": fixture_id,
        "fixture_date": fixture_date,
        "league_id": league_id,
        "league_name": league_name,
        "league_country": league_country,
        "home_id": home_id,
        "home_name": home_name,
        "away_id": away_id,
        "away_name": away_name,
        "home_matches_analyzed": len(home_matches),
        "home_0_0_1_1": home_draws,
        "away_matches_analyzed": len(away_matches),
        "away_0_0_1_1": away_draws,
        "total_0_0_1_1": total_draws,
        "total_games": total_games,
        "passes_7_on_14": passes,
        "created_at": datetime.utcnow().isoformat(timespec="seconds"),
    }

    registry[fixture_id_str] = entry
    return registry