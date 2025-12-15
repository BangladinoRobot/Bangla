import requests
from config import THE_ODDS_API_KEY

BASE_URL = "https://api.the-odds-api.com/v4"
BOOKMAKER_KEY = "bet365"

def get_soccer_keys():
    """Ritorna la lista degli sport_key che contengono 'soccer'."""
    url_sports = f"{BASE_URL}/sports"
    params = {"apiKey": THE_ODDS_API_KEY}
    resp = requests.get(url_sports, params=params)
    if resp.status_code != 200:
        print("Errore sports:", resp.status_code, resp.text)
        return []

    sports = resp.json()
    soccer_keys = [s for s in sports if "soccer" in s.get("key", "")]
    if not soccer_keys:
        print("Nessun sport di tipo soccer trovato.")
        return []

    print("Sport soccer trovati (prime 10):")
    for s in soccer_keys[:10]:
        print("-", s["key"], "|", s["title"])

    return [s["key"] for s in soccer_keys]

def process_league(sport_key):
    """Scarica e filtra le partite per un singolo sport_key di calcio."""
    print("\n==============================")
    print("Uso sport_key:", sport_key)

    url_odds = f"{BASE_URL}/sports/{sport_key}/odds"
    params_odds = {
        "apiKey": THE_ODDS_API_KEY,
        "regions": "eu",           # bookmaker europei
        "markets": "h2h,totals",   # 1X2 (h2h) + over/under (totals)
        "oddsFormat": "decimal",
        "bookmakers": BOOKMAKER_KEY
    }

    print("Richiedo odds per", sport_key, "dal bookmaker", BOOKMAKER_KEY, "...")
    resp_odds = requests.get(url_odds, params=params_odds)
    print("Status odds:", resp_odds.status_code)
    if resp_odds.status_code != 200:
        print("Risposta odds:", resp_odds.text)
        return

    events = resp_odds.json()
    print("Numero eventi con quote:", len(events))

    trovate = 0
    print("Partite dove X > 3.50 e Under 2.5 < 1.50:\n")

    for ev in events:
        home = ev.get("home_team")
        away = ev.get("away_team")

        draw_price = None
        under25_price = None

        for bk in ev.get("bookmakers", []):
            if bk.get("key") != BOOKMAKER_KEY:
                continue

            for market in bk.get("markets", []):
                key = market.get("key")

                if key == "h2h":
                    for o in market.get("outcomes", []):
                        if o.get("name") == "Draw":
                            draw_price = o.get("price")

                elif key == "totals":
                    for o in market.get("outcomes", []):
                        name = o.get("name")    # "Over" o "Under"
                        point = o.get("point")  # es. 2.5
                        price = o.get("price")  # quota
                        if name == "Under" and point == 2.5:
                            under25_price = price

        if draw_price is None or under25_price is None:
            continue

        try:
            draw_price_f = float(draw_price)
            under25_price_f = float(under25_price)
        except (TypeError, ValueError):
            continue

        if draw_price_f > 3.5 and under25_price_f < 1.5:
            trovate += 1
            print(f"- {home} vs {away}  | X @ {draw_price_f}  | Under 2.5 @ {under25_price_f}")

    if trovate == 0:
        print("Nessuna partita con X > 3.50 e Under 2.5 < 1.50 in questo campionato.")

def main():
    soccer_keys = get_soccer_keys()
    if not soccer_keys:
        return

    # per non bruciare troppi crediti, limitiamoci ai primi 5 campionati di calcio
    for sport_key in soccer_keys[:5]:
        process_league(sport_key)

if __name__ == "__main__":
    main()
