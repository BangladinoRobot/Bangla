import requests
from config import API_FOOTBALL_KEY

URL = "https://v3.football.api-sports.io/status"

headers = {
    "x-apisports-key": API_FOOTBALL_KEY
}

def main():
    print("Invio richiesta a API-Football...")
    response = requests.get(URL, headers=headers)
    print("Status code:", response.status_code)
    print("Risposta:")
    print(response.text)

if __name__ == "__main__":
    main()
