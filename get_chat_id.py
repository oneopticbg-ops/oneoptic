"""Пусни след като напишеш /start на бота си. Показва TG_CHAT_ID."""
import os, requests
r = requests.get(f"https://api.telegram.org/bot{os.environ['TG_BOT_TOKEN']}/getUpdates", timeout=30).json()
ids = {u["message"]["chat"]["id"] for u in r.get("result", []) if "message" in u}
print("TG_CHAT_ID =", ids or "не намерих съобщение - напиши /start на бота и опитай пак")
