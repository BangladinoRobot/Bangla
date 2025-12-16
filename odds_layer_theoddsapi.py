import json
import os
from datetime import datetime, timedelta
import requests

from config import THE_ODDS_API_KEY, DASHBOARD_URL
from telegram_utils import send_telegram_message

BASE_URL = "https://api.the-odds-api.com/v4"
BOOKMAKER_KEY = "bet365"

PASSED_FIXTURES_FILE = "passed_fixtures_stats.json"
ODDS_RESULTS_FILE = "odds_results.json"
STATS_SUMMARY_FILE = "stats_summary.json"


PLAN_LIMIT_FILE = "plan_limit_reached.json"

def load_stats_summary():
    """Carica il riepilogo statistico salvato da run_stats_on_league_fixtures.py."""
    if not os.path.exists(STATS_SUMMARY_FILE):
        return None
    try:
        with open(STATS_SUMMARY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None



def load_plan_limit_flag():
    """
    Ritorna (plan_limit_reached: bool, skipped_plan_limit: int)
    Legge plan_limit_reached.json scritto da stats_batch_apifootball.py.
    Considera valido solo se ts_utc è di oggi (UTC) quando presente.
    """
    try:
        import json
        if not os.path.exists(PLAN_LIMIT_FILE):
            return False, 0
        with open(PLAN_LIMIT_FILE, "r", encoding="utf-8") as f:
            d = json.load(f) or {}
        skipped = int(d.get("skipped_fixtures", 0) or 0)
        ts = d.get("ts_utc")
        if ts:
            try:
                if isinstance(ts, str) and ts.endswith("Z"):
                    ts = ts[:-1] + "+00:00"
                dt = datetime.fromisoformat(ts)
                if dt.date() != datetime.utcnow().date():
                    return False, 0
            except Exception:
                pass
        return True, skipped
    except Exception:
        # se il file è corrotto ma esiste, segnaliamo limite senza numero
        return True, 0

# ---------- UTILITÀ PER LE DATE / NOMI ----------

def parse_iso_datetime(s):
    """Parsa una stringa ISO (sia con 'Z' che con offset) in datetime, oppure None se fallisce."""
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None


def format_date_for_msg(s):
    """Formatta una stringa ISO in dd/mm/YYYY per i messaggi Telegram."""
    dt = parse_iso_datetime(s)
    if dt:
        return dt.strftime("%d/%m/%Y")
    return s or "?"


def normalize_team_name(name):
    """Normalizza il nome squadra per confronti (minuscolo, tolti spazi e caratteri base)."""
    if not name:
        return ""
    s = name.lower()
    for ch in [".", ",", "-", "_", "fc", "club"]:
        s = s.replace(ch, " ")
    s = "".join(s.split())
    return s


# ---------- CARICAMENTO PARTITE STATS-OK ----------

def load_passed_fixtures():
    if not os.path.exists(PASSED_FIXTURES_FILE):
        print(f"File {PASSED_FIXTURES_FILE} non trovato. Esegui prima run_stats_on_league_fixtures.py.")
        return []

    try:
        with open(PASSED_FIXTURES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                print(f"Contenuto di {PASSED_FIXTURES_FILE} non valido (non è una lista).")
                return []
            return data
    except Exception as e:
        print(f"Errore nel leggere {PASSED_FIXTURES_FILE}: {e}")
        return []


# ---------- ECCEZIONE PER LIMITE THE ODDS API ----------

class OddsApiLimitError(Exception):
    """Eccezione usata quando The Odds API segnala un limite di richieste."""
    pass


# ---------- THE ODDS API: SPORT DI CALCIO ----------

def get_soccer_sport_keys():
    """Restituisce la lista dei 'sport_key' che contengono 'soccer'."""
    url = f"{BASE_URL}/sports"
    params = {"apiKey": THE_ODDS_API_KEY}
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        print("Errore nel prendere la lista sport:", resp.status_code, resp.text)
        return []

    sports = resp.json()
    soccer_keys = [s["key"] for s in sports if "soccer" in s.get("key", "")]
    return soccer_keys


def fetch_odds_for_sport(sport_key):
    """
    Prende le quote per un singolo sport_key di calcio da bet365,
    con mercati h2h (1X2) e totals (over/under).
    Può sollevare OddsApiLimitError se la risposta indica un limite.
    """
    url = f"{BASE_URL}/sports/{sport_key}/odds"
    params = {
        "apiKey": THE_ODDS_API_KEY,
        "regions": "eu",
        "markets": "h2h,totals",
        "oddsFormat": "decimal",
        "bookmakers": BOOKMAKER_KEY,
    }
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        print(f"Errore odds per {sport_key}: {resp.status_code} {resp.text}")
        if resp.status_code in (402, 429):
            raise OddsApiLimitError(f"Limite The Odds API per {sport_key}: {resp.status_code}")
        return []

    try:
        data = resp.json()
        if not isinstance(data, list):
            return []
        return data
    except Exception:
        return []


# ---------- MATCHARE EVENTI CON LE PARTITE STATS-OK ----------

def match_event_with_fixture(event, fixture):
    """
    Ritorna True se l'evento di The Odds API sembra corrispondere
    alla fixture di API-Football, basandosi su nomi squadre + data.
    """
    ev_home = event.get("home_team")
    ev_away = event.get("away_team")

    fx_home = fixture.get("home_name")
    fx_away = fixture.get("away_name")

    nh_ev_home = normalize_team_name(ev_home)
    nh_ev_away = normalize_team_name(ev_away)
    nh_fx_home = normalize_team_name(fx_home)
    nh_fx_away = normalize_team_name(fx_away)

    names_match = (nh_ev_home == nh_fx_home) and (nh_ev_away == nh_fx_away)
    if not names_match:
        return False

    fx_date = parse_iso_datetime(fixture.get("date"))
    ev_date = parse_iso_datetime(event.get("commence_time"))

    if fx_date and ev_date:
        return fx_date.date() == ev_date.date()

    return True


def extract_odds_from_event(event):
    """
    Estrae X e Under 2.5 da un evento di The Odds API (bet365),
    ritorna (draw_price, under25_price) come float o (None, None) se mancano.
    """
    draw_price = None
    under25_price = None

    for bk in event.get("bookmakers", []):
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
                    name = o.get("name")
                    point = o.get("point")
                    price = o.get("price")
                    if name == "Under" and point == 2.5:
                        under25_price = price

    try:
        draw_price_f = float(draw_price) if draw_price is not None else None
        under25_price_f = float(under25_price) if under25_price is not None else None
    except (TypeError, ValueError):
        return None, None

    return draw_price_f, under25_price_f


# ---------- SUPPORTO RIEPILOGO ----------

def build_leagues_list(stats_summary, passed_fixtures):
    """Restituisce una lista di 'Paese - Nome lega' per il riepilogo."""
    if stats_summary and "leagues" in stats_summary:
        leagues = stats_summary.get("leagues") or []
        if leagues:
            return leagues

    leagues_set = set()
    for fx in passed_fixtures:
        country = fx.get("country") or "N/A"
        league_name = fx.get("league_name") or "N/A"
        leagues_set.add(f"{country} - {league_name}")

    return sorted(leagues_set)



def _apology_no_signals(plan_limit_reached: bool, skipped_plan_limit: int):
    out = []
    if plan_limit_reached:
        if skipped_plan_limit > 0:
            out.append(f"⚠️ Non ho potuto controllare {skipped_plan_limit} partite perché abbiamo raggiunto i limiti del piano.")
        out.append("<b>Oggi non ho segnalazioni da darvi perché abbiamo raggiunto i limiti del piano, vi chiedo scusa</b>")
    else:
        out.append("<b>Oggi non ho segnalazioni da darvi, vi chiedo scusa</b>")
    return out

# ---------- MAIN ----------

def main():
    now = datetime.now()
    header_date = now.strftime("%d/%m/%Y")
    header_time = now.strftime("%H:%M")

    passed_fixtures = load_passed_fixtures()
    print(f"Partite con statistiche OK (7/14) da controllare con le quote: {len(passed_fixtures)}")

    stats_summary = load_stats_summary()
    plan_limit_reached, skipped_plan_limit = load_plan_limit_flag()
    total_fixtures = 0
    if stats_summary:
        total_fixtures = stats_summary.get("total_fixtures", 0)

    leagues_list = build_leagues_list(stats_summary, passed_fixtures)

    today = now.date()
    end_date = today + timedelta(days=6)
    date_range_str = f"da oggi al {end_date.strftime('%d/%m/%Y')}"

    # Nessuna partita ha passato il 7/14
    if not passed_fixtures:
        lines = []
        lines.append("📊 Metodo 0-0 migliorato")
        lines.append(f"{header_date}, {header_time}")
        lines.append("")
        lines.append("📅 Date analizzate:")
        lines.append(date_range_str)
        lines.append(f'🔎 <a href="{DASHBOARD_URL}">Dettaglio sui campionati analizzati</a>')
        if total_fixtures == 0:
            lines.append("🌍 Nessuna partita di campionato in questi 7 giorni")
            lines.append("🏟 Partite analizzate: 0")
        else:
            if leagues_list:
                lines.append(f"🌍 Campionati coinvolti ({len(leagues_list)}):")
                for lg in leagues_list:
                    lines.append(f"• {lg}")
            lines.append(f"🏟 Partite analizzate: {total_fixtures}")
            lines.append("")
            lines.append("✅ Ultime partite con almeno sette 0-0 o 1-1: 0")

        lines.append("")
        lines.append("<b>Oggi non ho segnalazioni da darvi, vi chiedo scusa</b>")

        msg = "\n".join(lines)
        print(msg)
        try:
            send_telegram_message(msg, parse_mode="HTML")
        except Exception as e:
            print("Errore nell'invio del messaggio Telegram:", e)
        return

    # Da qui in poi: almeno una partita ha passato 7/14
    soccer_keys = get_soccer_sport_keys()
    print(f"Sport di calcio (soccer_*) trovati: {len(soccer_keys)}")

    if not soccer_keys:
        msg = (
            "📊 Metodo 0-0 migliorato\n"
            f"{header_date}, {header_time}\n\n"
            "Non riesco a recuperare gli sport di calcio da The Odds API. "
            "Oggi non posso verificare le quote, vi chiedo scusa"
        )
        print(msg)
        try:
            send_telegram_message(msg, parse_mode="HTML")
        except Exception as e:
            print("Errore nell'invio del messaggio Telegram:", e)
        return

    results = []
    odds_limit_reached = False

    try:
        for sport_key in soccer_keys:
            print(f"\n=== Controllo quote per {sport_key} ===")
            events = fetch_odds_for_sport(sport_key)
            print(f"Eventi trovati per {sport_key}: {len(events)}")

            for ev in events:
                for fixture in passed_fixtures:
                    if match_event_with_fixture(ev, fixture):
                        draw_price, under25_price = extract_odds_from_event(ev)

                        if draw_price is None or under25_price is None:
                            status = "STAT_OK_QUOTE_MISSING"
                        else:
                            if draw_price > 3.5 and under25_price < 1.5:
                                status = "AUTO_OK"
                            else:
                                status = "STAT_OK_QUOTE_FAIL"

                        results.append({
                            "fixture_id": fixture["fixture_id"],
                            "date": fixture["date"],
                            "country": fixture["country"],
                            "league_name": fixture["league_name"],
                            "home_name": fixture["home_name"],
                            "away_name": fixture["away_name"],
                            "total_00_11": fixture["total_00_11"],
                            "draw_price": draw_price,
                            "under25_price": under25_price,
                            "status": status,
                            "sport_key": sport_key,
                            "event_id": ev.get("id"),
                        })
    except OddsApiLimitError as e:
        print("Limite The Odds API raggiunto:", e)
        odds_limit_reached = True

    matched_ids = {r["fixture_id"] for r in results}
    for fixture in passed_fixtures:
        if fixture["fixture_id"] not in matched_ids:
            results.append({
                "fixture_id": fixture["fixture_id"],
                "date": fixture["date"],
                "country": fixture["country"],
                "league_name": fixture["league_name"],
                "home_name": fixture["home_name"],
                "away_name": fixture["away_name"],
                "total_00_11": fixture["total_00_11"],
                "draw_price": None,
                "under25_price": None,
                "status": "STAT_OK_QUOTE_MISSING",
                "sport_key": None,
                "event_id": None,
            })

    with open(ODDS_RESULTS_FILE, "w", encoding="utf-8") as f_out:
        json.dump(results, f_out, ensure_ascii=False, indent=2)

    auto_ok = [r for r in results if r["status"] == "AUTO_OK"]
    quote_missing = [r for r in results if r["status"] == "STAT_OK_QUOTE_MISSING"]

    print("\n==============================")
    print(f"Partite AUTO_OK (stats + quote ok): {len(auto_ok)}")
    print(f"Partite STAT_OK ma quote mancanti/da controllare a mano: {len(quote_missing)}")

    stats_pass_count = len(passed_fixtures)
    auto_ok_count = len(auto_ok)
    quote_missing_count = len(quote_missing)

    if total_fixtures <= 0:
        total_fixtures_display = stats_pass_count
    else:
        total_fixtures_display = total_fixtures

    lines = []
    lines.append("📊 Metodo 0-0 migliorato")
    lines.append(f"{header_date}, {header_time}")
    lines.append("")
    lines.append("📅 Date analizzate:")
    lines.append(date_range_str)
    lines.append(f'🔎 <a href="{DASHBOARD_URL}">Dettaglio sui campionati analizzati</a>')
    if leagues_list:
        lines.append(f"🌍 Campionati coinvolti ({len(leagues_list)}):")
        for lg in leagues_list:
            lines.append(f"• {lg}")
    lines.append(f"🏟 Partite analizzate: {total_fixtures_display}")
    lines.append("")
    lines.append(f"✅ Ultime partite con almeno sette 0-0 o 1-1: {stats_pass_count}")

    if auto_ok_count == 0:
        if odds_limit_reached and quote_missing_count > 0:
            lines.append(
                f"🎯 Quote con X ≥ 3.50 e Under 2.5 ≤ 1.50: "
                f"0 con quote verificate, {quote_missing_count} senza quote per limite richieste (bet365)"
            )
            lines.append("")
            lines.append("Partite da controllare manualmente (quote NON verificate):")
            for r in quote_missing:
                d = format_date_for_msg(r["date"])
                lines.append(
                    f"• {d} - {r['country']} - {r['league_name']} - "
                    f"{r['home_name']} vs {r['away_name']}"
                )
            lines.append("")
            lines.append("<b>Oggi non ho segnalazioni da darvi, vi chiedo scusa</b>")
        else:
            lines.append("🎯 Quote con X ≥ 3.50 e Under 2.5 ≤ 1.50: 0 (bet365)")
            lines.append("")
            lines.append(
                f"<b>Ci sono {stats_pass_count} partite interessanti a livello statistico, "
                "ma non rispettano le quote richieste, vi chiedo scusa</b>"
            )

        msg = "\n".join(lines)
        print(msg)
        try:
            send_telegram_message(msg, parse_mode="HTML")
        except Exception as e:
            print("Errore nell'invio del messaggio Telegram:", e)
        return

    if odds_limit_reached and quote_missing_count > 0:
        lines.append(
            f"🎯 Quote con X ≥ 3.50 e Under 2.5 ≤ 1.50: "
            f"{auto_ok_count} con quote verificate, {quote_missing_count} senza quote per limite richieste (bet365)"
        )
        lines.append("")
        lines.append(f"🧪 Segnalazioni Metodo 0-0 migliorato: {auto_ok_count} partite trovate")
        lines.append("")
        lines.append("Partite da controllare manualmente (quote NON verificate):")
        for r in quote_missing:
            d = format_date_for_msg(r["date"])
            lines.append(
                f"• {d} - {r['country']} - {r['league_name']} - "
                f"{r['home_name']} vs {r['away_name']}"
            )
        lines.append("")
        lines.append(
            "<b>Alcune partite statisticamente interessanti non hanno quote verificate "
            "a causa del limite giornaliero di The Odds API. "
            "Le ho elencate per facilitarvi il controllo manuale, vi chiedo scusa</b>"
        )
    else:
        lines.append(
            f"🎯 Quote con X ≥ 3.50 e Under 2.5 ≤ 1.50: {auto_ok_count} (bet365)"
        )
        lines.append("")
        lines.append(f"🧪 Segnalazioni Metodo 0-0 migliorato: {auto_ok_count} partite trovate")

    summary_msg = "\n".join(lines)
    print(summary_msg)
    try:
        send_telegram_message(summary_msg, parse_mode="HTML")
    except Exception as e:
        print("Errore nell'invio del messaggio Telegram (riepilogo):", e)

    for r in auto_ok:
        d = format_date_for_msg(r["date"])
        detail_lines = []
        detail_lines.append("🧪 Segnalazione Metodo 0-0 migliorato")
        detail_lines.append(f"📅 {d} - {r['country']} - {r['league_name']}")
        detail_lines.append(f"🏟 {r['home_name']} vs {r['away_name']}")
        detail_lines.append(f"- {r['total_00_11']}/14 partite finite 0-0 o 1-1")
        detail_lines.append(
            f"- X a {r['draw_price']}, Under 2.5 a {r['under25_price']} (bet365)"
        )
        detail_msg = "\n".join(detail_lines)
        print(detail_msg)
        try:
            send_telegram_message(detail_msg, parse_mode="HTML")
        except Exception as e:
            print("Errore nell'invio del messaggio Telegram (dettaglio):", e)


if __name__ == "__main__":
    main()
