import time
import requests

from config import TELEGRAM_TOKEN

# Canale da controllare (il Dottor Palinsesto)
CHANNEL_ID = -1003347502613

# Super user che possono usare il comando anche se non sono nel canale
SUPER_USERS = {71875799, 174147920}

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


def send_message(chat_id, text):
    try:
        requests.post(f"{BASE_URL}/sendMessage", data={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception as e:
        print("Errore send_message:", e)


def is_allowed_user(user_id: int) -> bool:
    """
    Ritorna True se:
    - l'utente è un super user, oppure
    - l'utente è membro del canale CHANNEL_ID.
    """
    if user_id in SUPER_USERS:
        return True

    try:
        resp = requests.get(
            f"{BASE_URL}/getChatMember",
            params={"chat_id": CHANNEL_ID, "user_id": user_id},
            timeout=10,
        )
        if resp.status_code != 200:
            print("getChatMember status:", resp.status_code, resp.text)
            return False

        data = resp.json()
        if not data.get("ok"):
            print("getChatMember not ok:", data)
            return False

        status = data["result"].get("status")
        # Consideriamo ammessi: creator, administrator, member, restricted
        return status in ("creator", "administrator", "member", "restricted")

    except Exception as e:
        print("Errore in is_allowed_user:", e)
        return False


def handle_info_command(chat_id: int, user_id: int):
    """
    Gestisce il comando /info0a0migliorato.
    """
    if not is_allowed_user(user_id):
        reply = (
            "Scusami amico, ma il mio padrone @theleonibus "
            "mi ha ordinato di non parlare con gli sconosciuti… :("
        )
        send_message(chat_id, reply)
        return

    # Testo con la spiegazione della strategia (sintetica)
    reply = (
        "🧠 Metodo 0-0 migliorato\n\n"
        "1) Considero solo partite di campionato nei prossimi 3 giorni.\n"
        "2) Per ogni partita guardo le ultime 7 gare ufficiali di entrambe le squadre "
        "(campionato, coppe e amichevoli): in totale 14 partite.\n"
        "3) Conto quante di queste 14 sono finite 0-0 o 1-1. "
        "La partita passa il filtro solo se almeno 7 su 14 sono 0-0 o 1-1.\n"
        "4) Solo per le partite che passano il filtro statistico, controllo le quote su bet365:\n"
        "   - quota X deve essere ≥ 3.50\n"
        "   - quota Under 2.5 deve essere ≤ 1.50\n"
        "5) Segnalo sul canale solo le partite che rispettano sia la parte statistica "
        "sia le quote richieste."
    )
    send_message(chat_id, reply)


def main():
    """
    Semplice long-polling che ascolta i messaggi privati
    e risponde solo al comando /info0a0migliorato.
    """
    offset = None

    while True:
        try:
            params = {"timeout": 20}
            if offset is not None:
                params["offset"] = offset

            resp = requests.get(f"{BASE_URL}/getUpdates", params=params, timeout=30)
            if resp.status_code != 200:
                print("getUpdates status:", resp.status_code, resp.text)
                time.sleep(5)
                continue

            data = resp.json()
            if not data.get("ok"):
                print("getUpdates not ok:", data)
                time.sleep(5)
                continue

            for update in data.get("result", []):
                offset = update["update_id"] + 1

                msg = update.get("message") or update.get("edited_message")
                if not msg:
                    continue

                chat = msg.get("chat", {})
                chat_type = chat.get("type")
                chat_id = chat.get("id")
                text = msg.get("text") or ""
                from_user = msg.get("from", {})
                user_id = from_user.get("id")

                if not text or not user_id:
                    continue

                # Rispondiamo solo alle chat private
                if chat_type != "private":
                    continue

                # Solo al comando /info0a0migliorato (anche se l'utente scrive altro dopo)
                first_word = text.strip().split()[0]
                if first_word == "/info0a0migliorato":
                    handle_info_command(chat_id, user_id)

        except Exception as e:
            print("Eccezione nel loop principale:", e)
            time.sleep(5)


if __name__ == "__main__":
    main()
