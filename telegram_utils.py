#!/usr/bin/env python3
import requests
from config import TELEGRAM_TOKEN, CHAT_ID


def send_telegram_message(text: str, chat_id: str = CHAT_ID, parse_mode: str = "HTML"):
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            },
            timeout=30,
        )
        if not resp.ok:
            print(f"Errore nell'invio del messaggio Telegram: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"Errore nell'invio del messaggio Telegram: {e}")
