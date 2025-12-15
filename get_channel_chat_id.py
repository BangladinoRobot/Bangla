import requests
from config import TELEGRAM_TOKEN

url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
resp = requests.get(url)
print("Status code:", resp.status_code)
print(resp.text)
