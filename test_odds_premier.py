import requests
from datetime import date
from config import API_FOOTBALL_KEY

BASE_URL = "https://v3.football.api-sports.io"
headers = {
    "x-apisports-key": API_FOOTBALL_KEY
}

def main():
    today = date.today().isoformat()
    year = date.today().year  # stagione dell'anno corrente

    print("Giorno:", today, "  stagione:", year)
    print("Cerco quote per Premier League (league=39)...")

    url = f"{BASE_URL}/odds"
    params = {
        "date": today,
        "league": 39,      # 39 = Premier League
        "season": year
    }

    resp = requests.get(url, headers=headers, params=params)
    print("Status code:", resp.status_code)
    print("Risposta grezza:")
    print(resp.text)

if __name__ == "__main__":
    main()
