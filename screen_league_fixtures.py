import requests
import json
import unicodedata
from datetime import date, timedelta
from config import API_FOOTBALL_KEY

BASE_URL = "https://v3.football.api-sports.io"
headers = {
    "x-apisports-key": API_FOOTBALL_KEY
}

# Guardiamo oggi + prossimi 7 giorni (8 giorni in totale)
MAX_DAYS_AHEAD = 7

# Paesi considerati "Sud America" per la priorità
SOUTH_AMERICA_COUNTRIES = {
    "Argentina",
    "Brazil",
    "Chile",
    "Colombia",
    "Peru",
    "Paraguay",
    "Uruguay",
    "Ecuador",
    "Bolivia",
    "Venezuela"
}

# Queste "pseudo-nazioni" indicano quasi sempre coppe / tornei internazionali
NON_DOMESTIC_COUNTRIES = {
    "world", "europe", "international", "uefa",
    "fifa", "conmebol", "afc", "caf", "concacaf", "ofc"
}

# Coppe / grandi tornei da ESCLUDERE SEMPRE (anche se hanno "league" nel nome)
EXPLICIT_CUP_NAME_PATTERNS = [
    # Europa
    "champions league",
    "uefa champions",
    "europa league",
    "conference league",
    "super cup",
    "uefa super",
    "european championship",

    # Sudamerica
    "copa libertadores",
    "libertadores",
    "copa sudamericana",
    "sudamericana",

    # Nord/Centro America
    "concacaf league",
    "concacaf champions",

    # Mondiali & affini
    "world cup",
    "club world cup",

    # Coppe nazionali specifiche
    "fa cup",
    "coppa italia",
    "copa del rey",
    "dfb-pokal",
    "dfb pokal",
    "taça de portugal",
    "taca de portugal",
    "taça da liga",
    "taca da liga",
    "copa do brasil",
    "coupe de france",
    "coupe de la ligue",
    "league cup",
    "efl cup",
    "carabao cup"
]

# Parole che tipicamente indicano COPPE
CUP_KEYWORDS = [
    "cup", "copa", "taça", "taca", "pokal", "trophée", "trophee",
    "trophy", "shield", "supercopa", "super cup", "supertaça",
    "super taca", "superliga cup"
]

# Amichevoli
FRIENDLY_KEYWORDS = [
    "friendly", "friendlies", "club friendlies"
]

# Qualificazioni / playoff
QUALIFICATION_KEYWORDS = [
    "qualification", "qualifying", "qualifiers",
    "play-offs", "playoffs", "play off", "preliminary round",
    "preliminary stage"
]

# Parole che tipicamente indicano un CAMPIONATO
LEAGUE_HINT_KEYWORDS = [
    "league", "liga", "ligue", "bundesliga", "premier",
    "division", "divisie", "serie", "superliga", "super league",
    "eredivisie", "allsvenskan", "j1 league", "k league",
    "süper lig", "super lig", "pro league", "championship"
]


def _normalize_text(s: str) -> str:
    """Minuscolo + rimozione accenti per confronti robusti."""
    s = s or ""
    s = s.lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s


def is_league_competition(league: dict) -> bool:
    """
    True = consideriamo questa competizione un CAMPIONATO.
    False = coppa / amichevole / qualificazione / torneo internazionale.
    """
    if not league:
        return False

    ltype = _normalize_text(league.get("type") or "")
    lname = _normalize_text(league.get("name") or "")
    lcountry = _normalize_text(league.get("country") or "")
    lid = league.get("id")

    # 1) Se l'API dice chiaramente league/cup, fidiamoci.
    if ltype == "league":
        return True
    if ltype == "cup":
        return False

    # 2) Se il "paese" è World / Europe / International / confederazioni,
    #    presumiamo torneo NON di campionato (Champions, Mondiali, ecc.)
    if lcountry in NON_DOMESTIC_COUNTRIES:
        # Se un domani hai qualche torneo da includere lo puoi whitelistarci qui per id
        # es: if lid in {123, 456}: return True
        return False

    # 3) Esclusione esplicita di grandi coppe conosciute
    for pat in EXPLICIT_CUP_NAME_PATTERNS:
        if pat in lname:
            return False

    # 4) Escludi tutto ciò che sembra coppa/amichevole/qualificazione
    for pat in CUP_KEYWORDS:
        if pat in lname:
            return False
    for pat in FRIENDLY_KEYWORDS:
        if pat in lname:
            return False
    for pat in QUALIFICATION_KEYWORDS:
        if pat in lname:
            return False

    # 5) Se il nome "assomiglia" chiaramente a un campionato, includilo
    for pat in LEAGUE_HINT_KEYWORDS:
        if pat in lname:
            return True

    # 6) Default: in dubbio, consideriamolo campionato.
    #    Meglio includere 1-2 coppe strane che perdere campionati veri.
    return True


def compute_priority(league: dict) -> int:
    """
    Ritorna un numero di priorità:
    0 = Sud America
    1 = Pakistan
    2 = Israel
    3 = tutto il resto
    """
    country = (league.get("country") or "").strip()
    if country in SOUTH_AMERICA_COUNTRIES:
        return 0
    if country == "Pakistan":
        return 1
    if country == "Israel":
        return 2
    return 3


def main():
    today = date.today()
    all_league_fixtures = []

    for offset in range(MAX_DAYS_AHEAD + 1):
        d = today + timedelta(days=offset)
        d_str = d.strftime("%Y-%m-%d")
        print(f"\n=== Giorno {d_str} ===")

        url = f"{BASE_URL}/fixtures"
        params = {"date": d_str}

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=20)
        except Exception as e:
            print("Errore nella richiesta HTTP:", e)
            continue

        print("Status code fixtures:", resp.status_code)

        if resp.status_code != 200:
            print("Risposta non OK dalla API:", resp.text[:300])
            continue

        try:
            data = resp.json()
        except Exception as e:
            print("Errore nel fare .json():", e)
            continue

        errors = data.get("errors") or {}
        if "plan" in errors:
            print("⚠️ Limite piano API-Football:", errors["plan"])
            print("Mi fermo qui: il piano free non permette di andare oltre questa data.")
            break

        day_fixtures = data.get("response") or []

        print("Partite totali (tutte le competizioni):", len(day_fixtures))

        league_fixtures = [
            f for f in day_fixtures
            if is_league_competition(f.get("league", {}) or {})
        ]

        print("Partite di campionato (League):", len(league_fixtures))

        all_league_fixtures.extend(league_fixtures)

    print("\n==============================")
    print("Totale partite di campionato trovate nei prossimi giorni:", len(all_league_fixtures))

    # Ordiniamo per priorità (Sud America, Pakistan, Israel, altri), poi paese, nome lega, data
    def sort_key(f):
        league = f.get("league", {}) or {}
        fixture = f.get("fixture", {}) or {}
        country = league.get("country") or ""
        name = league.get("name") or ""
        fdate = fixture.get("date") or ""
        priority = compute_priority(league)
        return (priority, country, name, fdate)

    all_league_fixtures.sort(key=sort_key)

    print("\nElenco partite di campionato ordinate per priorità:\n")
    for f in all_league_fixtures:
        fixture = f.get("fixture", {}) or {}
        league = f.get("league", {}) or {}
        teams = f.get("teams", {}) or {}
        dt = fixture.get("date")
        country = league.get("country")
        lname = league.get("name")
        hname = teams.get("home", {}).get("name")
        aname = teams.get("away", {}).get("name")
        print(f"- {dt} | {country} - {lname} | {hname} vs {aname}")

    # Prepariamo il JSON per gli script successivi
    fixtures_for_json = []
    for f in all_league_fixtures:
        fixture = f.get("fixture", {}) or {}
        league = f.get("league", {}) or {}
        teams = f.get("teams", {}) or {}

        fixtures_for_json.append({
            "fixture_id": fixture.get("id"),
            "fixture_date": fixture.get("date"),
            "league_id": league.get("id"),
            "league_name": league.get("name"),
            "league_country": league.get("country"),
            "home_id": teams.get("home", {}).get("id"),
            "away_id": teams.get("away", {}).get("id"),
            "home_name": teams.get("home", {}).get("name"),
            "away_name": teams.get("away", {}).get("name"),
        })

    with open("league_fixtures.json", "w", encoding="utf-8") as jf:
        json.dump(fixtures_for_json, jf, ensure_ascii=False, indent=2)

    print(f"\nSalvate {len(fixtures_for_json)} partite di campionato in league_fixtures.json")


if __name__ == "__main__":
    main()
