import requests
from config import API_FOOTBALL_KEY

BASE_URL = "https://v3.football.api-sports.io"
headers = {
    "x-apisports-key": API_FOOTBALL_KEY
}

def get_fixture(fixture_id):
    url = f"{BASE_URL}/fixtures"
    params = {"id": fixture_id}
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("response"):
        raise ValueError(f"Nessuna fixture trovata per id {fixture_id}")
    return data["response"][0]

def get_last_matches(team_id, n=7):
    url = f"{BASE_URL}/fixtures"
    params = {
        "team": team_id,
        "last": n
    }
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", [])

def count_00_11(fixtures):
    count = 0
    for f in fixtures:
        goals_home = f["goals"]["home"]
        goals_away = f["goals"]["away"]
        if goals_home is None or goals_away is None:
            continue
        if (goals_home == 0 and goals_away == 0) or (goals_home == 1 and goals_away == 1):
            count += 1
    return count

def main():
    # QUI mettiamo un fixture_id di test
    fixture_id = 1456961

    print(f"Analizzo fixture id {fixture_id}...")

    fixture = get_fixture(fixture_id)
    home_team = fixture["teams"]["home"]
    away_team = fixture["teams"]["away"]

    home_id = home_team["id"]
    away_id = away_team["id"]
    home_name = home_team["name"]
    away_name = away_team["name"]

    print(f"Partita: {home_name} vs {away_name}")
    print(f"Home team id: {home_id}, Away team id: {away_id}")

    # Ultime 7 partite di ciascuna squadra
    print("\nRecupero ultime 7 partite del", home_name)
    last_home = get_last_matches(home_id, 7)
    print("Trovate", len(last_home), "partite.")

    print("Recupero ultime 7 partite del", away_name)
    last_away = get_last_matches(away_id, 7)
    print("Trovate", len(last_away), "partite.")

    # Conta 0–0 e 1–1
    home_00_11 = count_00_11(last_home)
    away_00_11 = count_00_11(last_away)
    total_00_11 = home_00_11 + away_00_11

    print(f"\n{home_name}: {home_00_11} partite 0–0 o 1–1 su 7")
    print(f"{away_name}: {away_00_11} partite 0–0 o 1–1 su 7")
    print(f"Totale: {total_00_11} su 14")

    if total_00_11 >= 7:
        print("✅ La partita PASSA la regola 7 su 14 (0–0 / 1–1).")
    else:
        print("❌ La partita NON passa la regola 7 su 14.")

if __name__ == "__main__":
    main()
