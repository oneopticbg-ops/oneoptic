"""Чете одобренията от Telegram и публикува одобрените постове в Instagram."""
import os, json, glob, time, requests
G = "https://graph.facebook.com/v21.0"
TOK, UID = os.environ["IG_TOKEN"], os.environ["IG_USER_ID"]
TG = f"https://api.telegram.org/bot{os.environ['TG_BOT_TOKEN']}"; CHAT = str(os.environ["TG_CHAT_ID"])
REPO = os.environ["GITHUB_REPOSITORY"]; BR = os.environ.get("GITHUB_REF_NAME", "main")
OFF = "data/tg_offset.txt"
os.makedirs("data", exist_ok=True); os.makedirs("queue", exist_ok=True)

def load(pid): return json.load(open(f"queue/{pid}/post.json"))
def save(p): json.dump(p, open(f"queue/{p['id']}/post.json", "w"), ensure_ascii=False, indent=1)

off = int(open(OFF).read()) if os.path.exists(OFF) else 0
for u in requests.get(f"{TG}/getUpdates", params={"offset": off, "timeout": 0}, timeout=60).json().get("result", []):
    off = u["update_id"] + 1; cb = u.get("callback_query")
    if cb and str(cb["message"]["chat"]["id"]) == CHAT:
        act, pid = cb["data"].split(":", 1)
        if os.path.exists(f"queue/{pid}/post.json"):
            p = load(pid)
            if p["status"] == "pending": p["status"] = "approved" if act == "a" else "rejected"; save(p)
        requests.post(f"{TG}/answerCallbackQuery", data={"callback_query_id": cb["id"], "text": "Прието"})
open(OFF, "w").write(str(off))

def api(path, **d):
    d["access_token"] = TOK; r = requests.post(f"{G}/{path}", data=d, timeout=120).json()
    if "error" in r: raise RuntimeError(r["error"]); 
    return r

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
        requests.post(f"{TG}/sendMessage", data={"chat_id": CHAT, "text": f"Публикувано: {p['id']}"})
    except Exception as e:
        p["status"] = "error"; requests.post(f"{TG}/sendMessage", data={"chat_id": CHAT, "text": f"Грешка {p['id']}: {e}"})
    save(p)
