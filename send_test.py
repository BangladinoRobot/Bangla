import requests
from config import TELEGRAM_TOKEN, CHAT_ID

def main():
    url = "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": "✅ Messaggio di test dal Raspberry Pi"
    }
    response = requests.post(url, data=data)
    print("Status code:", response.status_code)
    print("Response text:", response.text)

if __name__ == "__main__":
    main()
