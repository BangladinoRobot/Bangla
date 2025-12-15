import requests
from datetime import date
from config import API_FOOTBALL_KEY

BASE_URL = "https://v3.football.api-sports.io"
headers = {
    "x-apisports-key": API_FOOTBALL_KEY
}

def main():
    today = date.today().isoformat()  # formato YYYY-MM-DD
    print("Cerco le partite per il giorno:", today)

    url = f"{BASE_URL}/fixtures"
    params = {
        "date": today
    }

    response = requests.get(url, headers=headers, params=params)
    print("Status code:", response.status_code)

    data = response.json()
    results = data.get("results", 0)
    print("Numero totale di partite trovate:", results)

    print("\nPrime 10 partite:")
    for item in data.get("response", [])[:10]:
        fixture_id = item["fixture"]["id"]
        league = item["league"]["name"]
        country = item["league"]["country"]
        home = item["teams"]["home"]["name"]
        away = item["teams"]["away"]["name"]
        print(f"{fixture_id} | {country} - {league}: {home} vs {away}")

if __name__ == "__main__":
    main()
