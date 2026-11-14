"""Чете отговорите от Telegram (одобрения и върнати AI снимки) и публикува одобрените постове в Instagram."""
import os, sys, json, glob, time, io, subprocess, requests
try:
    from PIL import Image
except ImportError:  # Pillow се инсталира автоматично, ако липсва
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "pillow"]); from PIL import Image
from ad import finish_ad

G = "https://graph.facebook.com/v26.0"
TOK, UID = os.environ.get("IG_TOKEN", ""), os.environ.get("IG_USER_ID", "")
BOT = os.environ.get("TG_BOT_TOKEN", ""); TG = f"https://api.telegram.org/bot{BOT}"; CHAT = str(os.environ.get("TG_CHAT_ID", ""))
REPO = os.environ.get("GITHUB_REPOSITORY", ""); BR = os.environ.get("GITHUB_REF_NAME", "main")
OFF = "data/tg_offset.txt"
os.makedirs("data", exist_ok=True); os.makedirs("queue", exist_ok=True)


def load(pid): return json.load(open(f"queue/{pid}/post.json"))
def save(p): json.dump(p, open(f"queue/{p['id']}/post.json", "w"), ensure_ascii=False, indent=1)
def say(text, **kw): requests.post(f"{TG}/sendMessage", data={"chat_id": CHAT, "text": text, **kw})


def all_posts():
    out = []
    for f in sorted(glob.glob("queue/*/post.json")):
        try: out.append(json.load(open(f)))
        except Exception: pass
    return out


def preview(p):
    kb = {"inline_keyboard": [[{"text": "✅ Одобри", "callback_data": f"a:{p['id']}"}, {"text": "❌ Откажи", "callback_data": f"r:{p['id']}"}]]}
    cap = (f"[AI] {p['caption']}\n\n{' '.join(p['hashtags'])}\n⚠️ Провери дали рамката съвпада с реалния модел.")[:1000]
    requests.post(f"{TG}/sendPhoto", data={"chat_id": CHAT, "caption": cap, "reply_markup": json.dumps(kb)}, files={"photo": open(f"queue/{p['id']}/media.jpg", "rb")}, timeout=300)


def handle_image(msg):
    """Върната от потребителя AI снимка -> реклама с марка и слоган -> преглед за одобрение."""
    file_id = None
    if msg.get("photo"): file_id = msg["photo"][-1]["file_id"]
    elif msg.get("document", {}).get("mime_type", "").startswith("image/"): file_id = msg["document"]["file_id"]
    if not file_id: return
    waiting = [p for p in all_posts() if p.get("status") == "awaiting_image"]
    reply_id = (msg.get("reply_to_message") or {}).get("message_id")
    target = next((p for p in waiting if reply_id and reply_id in p.get("tg_msgs", [])), None) or (waiting[0] if waiting else None)
    if not target: say("Нямам задача, която чака снимка. Пусни `generate`, за да получиш нови."); return
    info = requests.get(f"{TG}/getFile", params={"file_id": file_id}, timeout=60).json()
    raw = requests.get(f"https://api.telegram.org/file/bot{BOT}/{info['result']['file_path']}", timeout=120).content
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    d = f"queue/{target['id']}"; im.save(f"{d}/raw.jpg", quality=95)
    finish_ad(im, target.get("brand", ""), target.get("slogan", ""), target.get("layout", "bottom"), target.get("store", "OneOptic")).save(f"{d}/media.jpg", quality=93)
    target["media"] = "media.jpg"; target["status"] = "pending"; save(target); preview(target)


def process_updates():
    off = int(open(OFF).read()) if os.path.exists(OFF) else 0
    for u in requests.get(f"{TG}/getUpdates", params={"offset": off, "timeout": 0}, timeout=60).json().get("result", []):
        off = u["update_id"] + 1; cb = u.get("callback_query"); msg = u.get("message")
        try:
            if cb and str(cb["message"]["chat"]["id"]) == CHAT:
                act, pid = cb["data"].split(":", 1)
                if os.path.exists(f"queue/{pid}/post.json"):
                    p = load(pid)
                    if p["status"] == "pending": p["status"] = "approved" if act == "a" else "rejected"; save(p)
                requests.post(f"{TG}/answerCallbackQuery", data={"callback_query_id": cb["id"], "text": "Прието"})
            elif msg and str(msg["chat"]["id"]) == CHAT:
                handle_image(msg)
        except Exception as e:
            print("Грешка при обработка на съобщение:", str(e)[:300]); say(f"Не успях да обработя съобщението: {str(e)[:200]}")
    open(OFF, "w").write(str(off))


def api(path, **d):
    d["access_token"] = TOK; r = requests.post(f"{G}/{path}", data=d, timeout=120).json()
    if "error" in r: raise RuntimeError(r["error"])
    return r


def publish_approved():
    for f in sorted(glob.glob("queue/*/post.json")):
        p = json.load(open(f))
        if p["status"] != "approved": continue
        url = f"https://raw.githubusercontent.com/{REPO}/{BR}/queue/{p['id']}/{p['media']}"
        cap = p["caption"] + "\n\n" + " ".join(p["hashtags"])
        try:
            if p["format"] == "reel":
                c = api(f"{UID}/media", media_type="REELS", video_url=url, caption=cap, share_to_feed="true")["id"]
                for _ in range(40):
                    st = requests.get(f"{G}/{c}", params={"fields": "status_code", "access_token": TOK}).json().get("status_code")
                    if st == "FINISHED": break
                    if st == "ERROR": raise RuntimeError("video processing error")
                    time.sleep(15)
            else:
                c = api(f"{UID}/media", image_url=url, caption=cap)["id"]
            api(f"{UID}/media_publish", creation_id=c); p["status"] = "published"
            say(f"Публикувано: {p['id']}")
        except Exception as e:
            p["status"] = "error"; say(f"Грешка {p['id']}: {e}")
        save(p)


if __name__ == "__main__":
    process_updates(); publish_approved()
