import requests
from config import THE_ODDS_API_KEY

BASE_URL = "https://api.the-odds-api.com/v4"

def main():
    # 1) chiediamo la lista degli sport disponibili
    url_sports = f"{BASE_URL}/sports"
    params_sports = {
        "apiKey": THE_ODDS_API_KEY
    }
    print("Richiedo lista sport...")
    resp_sports = requests.get(url_sports, params=params_sports)
    print("Status sports:", resp_sports.status_code)
    if resp_sports.status_code != 200:
        print("Risposta sports:", resp_sports.text)
        return

    sports = resp_sports.json()
    # cerchiamo un campionato di calcio, es. Premier League (di solito 'soccer_epl')
    soccer_keys = [s for s in sports if "soccer" in s.get("key", "")]
    print("Sport di tipo soccer trovati (prime 5):")
    for s in soccer_keys[:5]:
        print("-", s["key"], "|", s["title"])

    if not soccer_keys:
        print("Nessun sport soccer trovato, esco.")
        return

    # 2) prendiamo il primo soccer trovato e chiediamo le quote 'totals' (over/under)
    sport_key = soccer_keys[0]["key"]
    print("\nUso sport_key:", sport_key)

    url_odds = f"{BASE_URL}/sports/{sport_key}/odds"
    params_odds = {
        "apiKey": THE_ODDS_API_KEY,
        "regions": "eu",          # bookmaker europei
        "markets": "totals",      # mercato over/under
        "oddsFormat": "decimal"
    }
    print("Richiedo odds per", sport_key, "...")
    resp_odds = requests.get(url_odds, params=params_odds)
    print("Status odds:", resp_odds.status_code)

    if resp_odds.status_code != 200:
        print("Risposta odds:", resp_odds.text)
        return

    events = resp_odds.json()
    print("Numero eventi con quote:", len(events))

    # stampiamo i primi 3 eventi con una quota totals trovata
    for ev in events[:3]:
        home = ev.get("home_team")
        away = ev.get("away_team")
        sport_key_ev = ev.get("sport_key")
        print(f"\nPartita: {home} vs {away}  ({sport_key_ev})")

        for bk in ev.get("bookmakers", []):
            title = bk.get("title")
            for market in bk.get("markets", []):
                if market.get("key") == "totals":
                    outcomes = market.get("outcomes", [])
                    print("  Bookmaker:", title)
                    for o in outcomes:
                        name = o.get("name")      # es. Over, Under
                        point = o.get("point")    # es. 2.5
                        price = o.get("price")    # quota decimale
                        print(f"    {name} {point} @ {price}")

if __name__ == "__main__":
    main()
