import sys
import requests
from datetime import date
from collections import Counter
from config import API_FOOTBALL_KEY

BASE_URL = "https://v3.football.api-sports.io"

def fetch_fixtures(d: str):
    url = f"{BASE_URL}/fixtures"
    headers = {
        "x-apisports-key": API_FOOTBALL_KEY
    }
    params = {
        "date": d
    }

    print(f"→ Chiamata API-Football /fixtures per la data: {d}")
    resp = requests.get(url, headers=headers, params=params, timeout=20)
    print("HTTP status:", resp.status_code)

    try:
        data = resp.json()
    except Exception as e:
        print("Errore nel fare .json():", e)
        return []

    print("API 'errors':", data.get("errors"))
    print("API 'results':", data.get("results"))
    fixtures = data.get("response", []) or []
    return fixtures

def main():
    # Data da riga di comando, altrimenti oggi
    if len(sys.argv) > 1:
        d = sys.argv[1]
    else:
        d = date.today().strftime("%Y-%m-%d")

    print(f"\n=== DEBUG FIXTURES API-FOOTBALL ===")
    print(f"Giorno richiesto: {d}\n")

    fixtures = fetch_fixtures(d)
    print(f"\nFixture totali ricevute: {len(fixtures)}\n")

    # Conteggio per league.type
    type_counter = Counter()
    for f in fixtures:
        league = f.get("league", {}) or {}
        ltype = league.get("type")
        type_counter[ltype] += 1

    print("Conteggio per league.type:")
    if not type_counter:
        print("  (nessuna fixture ricevuta)")
    else:
        for t, c in type_counter.items():
            print(f"  {t}: {c}")
    print()

    # Mostriamo le prime 30 fixture
    print("Prime fixture (max 30):\n")
    for i, fixture in enumerate(fixtures[:30], start=1):
        league = fixture.get("league", {}) or {}
        teams = fixture.get("teams", {}) or {}
        fid   = fixture.get("id")
        fdate = fixture.get("date")
        lname = league.get("name")
        lcountry = league.get("country")
        ltype = league.get("type")
        hname = teams.get("home", {}).get("name")
        aname = teams.get("away", {}).get("name")

        print(f"{i:02d}) id={fid} | {fdate} | {lcountry} - {lname} "
              f"(type={ltype}) | {hname} vs {aname}")

    print("\n=== FINE DEBUG ===\n")

if __name__ == "__main__":
    main()
