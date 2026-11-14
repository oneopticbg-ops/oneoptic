"""Проверява всички ключове и настройки и казва на български какво липсва."""
import os, glob, requests
ok = True
def res(name, good, hint=""):
    global ok; ok &= bool(good); print(("✅ " if good else "❌ ") + name + ("" if good else f"  -> {hint}"))

for k in ["IG_TOKEN", "IG_USER_ID", "GEMINI_API_KEY", "TG_BOT_TOKEN", "TG_CHAT_ID"]:
    res(f"secret {k}", os.environ.get(k), "добави го в Settings > Secrets and variables > Actions > Secrets")
photos = [p for p in glob.glob("products/*") if p.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
res(f"продуктови снимки в products/ ({len(photos)})", len(photos) >= 3, "качи поне 3 свои снимки в папка products/")
fonts = glob.glob("fonts/*.ttf")
res(f"шрифтове в fonts/ ({len(fonts)} от 7)", len(fonts) >= 7, "качи папката fonts от пакета")
res("design.py е качен", os.path.exists("design.py"), "качи design.py в основата на репото")
try:
    r = requests.get(f"https://graph.facebook.com/v26.0/{os.environ['IG_USER_ID']}", params={"fields": "username,followers_count", "access_token": os.environ["IG_TOKEN"]}, timeout=30).json()
    res(f"Instagram връзка ({r.get('username')})", "username" in r, str(r.get("error", {}).get("message", r)))
except Exception as e: res("Instagram връзка", False, str(e))
try:
    r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{os.environ.get('GEMINI_MODEL','gemini-2.5-flash')}:generateContent",
        params={"key": os.environ["GEMINI_API_KEY"]}, json={"contents": [{"parts": [{"text": "кажи ок"}]}]}, timeout=60).json()
    res("Gemini ключ", "candidates" in r, str(r.get("error", {}).get("message", r)))
except Exception as e: res("Gemini ключ", False, str(e))
om = os.environ.get("OPENAI_IMAGE_MODEL") or "gpt-image-2.5-sunburst"
if os.environ.get("OPENAI_API_KEY"):
    try:
        r = requests.get(f"https://api.openai.com/v1/models/{om}", headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]}, timeout=30)
        res(f"OpenAI снимки като в ChatGPT ({om})", r.status_code == 200, f"{r.status_code}: {r.text[:250]} -> провери ключа, добавени ли са кредити и дали моделът е наличен за акаунта ти")
    except Exception as e: res("OpenAI", False, str(e))
else:
    print("ℹ️  OpenAI ключ не е добавен (OPENAI_API_KEY) - AI снимките ще са от Gemini или студийни")
try:
    model = os.environ.get("GEMINI_IMAGE_MODEL") or "gemini-2.5-flash-image"
    r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent", params={"key": os.environ["GEMINI_API_KEY"]}, timeout=120,
        json={"contents": [{"parts": [{"text": "A single red circle on a white background, flat illustration"}]}], "generationConfig": {"responseModalities": ["IMAGE"]}}).json()
    parts = (r.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
    ok_img = any(p.get("inlineData") or p.get("inline_data") for p in parts)
    res(f"AI снимки ({model})", ok_img, "Google не позволява AI снимки с този ключ: " + str(r.get("error", {}).get("message", r))[:300] + " -> постовете ще са студийни снимки без AI")
except Exception as e: res("AI снимки", False, str(e))
try:
    r = requests.get(f"https://api.telegram.org/bot{os.environ['TG_BOT_TOKEN']}/getMe", timeout=30).json()
    res("Telegram бот", r.get("ok"), "провери токена от @BotFather")
    r = requests.post(f"https://api.telegram.org/bot{os.environ['TG_BOT_TOKEN']}/sendMessage", data={"chat_id": os.environ["TG_CHAT_ID"], "text": "✅ Връзката работи"}, timeout=30).json()
    res("Telegram съобщение до теб", r.get("ok"), "първо напиши /start на бота си, после провери TG_CHAT_ID: " + str(r.get("description")))
except Exception as e: res("Telegram", False, str(e))
print("\nВСИЧКО Е НАРЕДЕНО ✅" if ok else "\nИма липсващи неща ❌ - оправи ги по списъка горе и пусни проверката пак")
