import requests
from datetime import date
from config import API_FOOTBALL_KEY

BASE_URL = "https://v3.football.api-sports.io"
headers = {
    "x-apisports-key": API_FOOTBALL_KEY
}

def get_under25_odds(fixture_id):
    """Ritorna la quota Under 2.5 (float) per una partita, oppure None se non trovata."""
    url = f"{BASE_URL}/odds"
    params = {
        "fixture": fixture_id
    }
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        print(f"  [fixture {fixture_id}] errore odds, status {resp.status_code}")
        return None

    data = resp.json()
    for item in data.get("response", []):
        for bookmaker in item.get("bookmakers", []):
            for bet in bookmaker.get("bets", []):
                if bet.get("name") == "Under/Over":
                    for val in bet.get("values", []):
                        if val.get("value") == "Under 2.5":
                            odd_str = val.get("odd")
                            try:
                                return float(odd_str)
                            except (TypeError, ValueError):
                                return None
    return None

def main():
    today = date.today().isoformat()
    print("Cerco le partite per il giorno:", today)

    # 1) prendo le partite di oggi (come in test_fixtures)
    url = f"{BASE_URL}/fixtures"
    params = {"date": today}
    resp = requests.get(url, headers=headers, params=params)
    print("Status code fixtures:", resp.status_code)
    data = resp.json()
    fixtures = data.get("response", [])

    print("Numero partite:", len(fixtures))
    print("\nPrime 10 partite con eventuale quota Under 2.5:\n")

    for item in fixtures[:10]:
        fixture_id = item["fixture"]["id"]
        home = item["teams"]["home"]["name"]
        away = item["teams"]["away"]["name"]

        odd_u25 = get_under25_odds(fixture_id)
        if odd_u25 is not None:
            print(f"{fixture_id}: {home} vs {away}  | Under 2.5 = {odd_u25}")
        else:
            print(f"{fixture_id}: {home} vs {away}  | Under 2.5 NON trovata")

if __name__ == "__main__":
    main()
