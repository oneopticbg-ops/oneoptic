"""Генерира чернови (снимка/Reel) + копи на български и ги праща в Telegram за одобрение."""
import os, json, random, subprocess, time, requests, textwrap, glob
from PIL import Image, ImageDraw, ImageFont
BRAND = os.environ.get("BRAND_NAME", "нашата оптика")
N = int(os.environ.get("POSTS_PER_RUN", "3"))
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
TG = f"https://api.telegram.org/bot{os.environ.get('TG_BOT_TOKEN', '')}"
CHAT = os.environ.get("TG_CHAT_ID", "")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
DRY = os.environ.get("DRY_RUN") == "1"

def ask_gemini(prompt):
    if os.environ.get("MOCK_GEMINI"):
        return json.loads(os.environ["MOCK_GEMINI"])
    last = None
    for attempt in range(3):
        try:
            r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
                params={"key": os.environ["GEMINI_API_KEY"]}, timeout=120,
                json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}})
            data = json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])
            if isinstance(data, dict):
                data = next((v for v in data.values() if isinstance(v, list)), [data])
            return data
        except Exception as e:
            last = e; time.sleep(5)
    raise RuntimeError(f"Gemini не отговори коректно: {last}")

def render(photo, text, size, brand_line=True):
    im = Image.open(photo).convert("RGB"); W, H = size
    s = max(W / im.width, H / im.height); im = im.resize((int(im.width * s), int(im.height * s)))
    l, t = (im.width - W) // 2, (im.height - H) // 2; im = im.crop((l, t, l + W, t + H))
    ov = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(ov)
    for y in range(int(H * .55), H):
        d.line([(0, y), (W, y)], fill=(0, 0, 0, int(190 * (y - H * .55) / (H * .45))))
    im = Image.alpha_composite(im.convert("RGBA"), ov); d = ImageDraw.Draw(im)
    try: f, fs = ImageFont.truetype(FONT, W // 15), ImageFont.truetype(FONT, W // 32)
    except OSError: f = fs = ImageFont.load_default()
    y = H - int(H * .08) - (len(textwrap.wrap(text, 24)) * (W // 12))
    for line in textwrap.wrap(text, 24):
        d.text((W // 12, y), line, font=f, fill="white"); y += W // 12
    if brand_line: d.text((W // 12, H - int(H * .06)), BRAND.upper(), font=fs, fill=(220, 190, 140))
    return im.convert("RGB")

def tg_send(post, media_path):
    if DRY: print("DRY_RUN: пропускам Telegram за", media_path); return
    kb = {"inline_keyboard": [[{"text": "✅ Одобри", "callback_data": f"a:{post['id']}"},
                               {"text": "❌ Откажи", "callback_data": f"r:{post['id']}"}]]}
    cap = (f"[{post['format']}] {post['caption']}\n\n{' '.join(post['hashtags'])}")[:1000]
    kind, field = ("sendVideo", "video") if post["format"] == "reel" else ("sendPhoto", "photo")
    requests.post(f"{TG}/{kind}", data={"chat_id": CHAT, "caption": cap, "reply_markup": json.dumps(kb)},
                  files={field: open(media_path, "rb")}, timeout=300)

ins = json.load(open("data/insights.json")) if os.path.exists("data/insights.json") else {"own_top": [], "competitors": []}
photos = [p for p in glob.glob("products/*") if p.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
os.makedirs("queue", exist_ok=True); os.makedirs("data", exist_ok=True)
assert photos, "Сложи продуктови снимки в папка products/"
best = ins["competitors"][0] if ins["competitors"] else None
brief = {
 "наши_най-добри": [(p.get("caption") or "")[:200] for p in ins["own_top"][:5]],
 "водещ_конкурент": best and {"акаунт": best["username"], "ER": best["avg_er"],
     "най-добри_постове": [{"тип": p["media_type"], "текст": (p.get("caption") or "")[:200]} for p in best["top_posts"][:5]]},
}
prompt = f"""Ти си social media мениджър на оптика "{BRAND}" (диоптрични и слънчеви очила) в България.
Анализ на какво работи: {json.dumps(brief, ensure_ascii=False)}
Научи СТРУКТУРАТА и ФОРМАТИТЕ (кукичка, дължина, въпроси, CTA), не копирай текстове.
Тон: микс от луксозен и приятелски. Език: български. Без здравни обещания ("подобрява зрението"), без цени и отстъпки,
без твърдения за марки, които не са дадени. Налични снимки (имена на файлове): {[os.path.basename(p) for p in photos]}.
Върни JSON списък от {N} поста (максимум 1 с format="reel", другите "photo"). Всеки: 
{{"format":"photo|reel","overlay":"до 8 думи върху изображението","caption":"копи с кукичка и CTA","hashtags":["8-12 хаштага"],"photos":["файл(ове); 1 за photo, 3-4 за reel"]}}"""
ideas = [i for i in ask_gemini(prompt) if isinstance(i, dict) and i.get("caption")][:N]
assert ideas, "Gemini не върна валидни идеи"
for idea in ideas:
    idea.setdefault("format", "photo"); idea.setdefault("overlay", ""); idea.setdefault("hashtags", []); idea.setdefault("photos", [])
    idea["format"] = "reel" if idea["format"] == "reel" else "photo"
    pid = time.strftime("%Y%m%d-%H%M%S") + f"-{random.randint(100,999)}"; d = f"queue/{pid}"; os.makedirs(d)
    files = [f"products/{os.path.basename(x)}" for x in idea["photos"] if os.path.exists(f"products/{os.path.basename(x)}")] or [random.choice(photos)]
    if idea["format"] == "reel":
        for i, f in enumerate(files): render(f, idea["overlay"] if i == 0 else "", (1080, 1920), i == len(files) - 1).save(f"{d}/f{i+1}.jpg")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "1/3", "-i", f"{d}/f%d.jpg", "-c:v", "libx264",
                        "-r", "30", "-pix_fmt", "yuv420p", f"{d}/media.mp4"], check=True); media = "media.mp4"
        for x in glob.glob(f"{d}/f*.jpg"): os.remove(x)
    else:
        render(files[0], idea["overlay"], (1080, 1350)).save(f"{d}/media.jpg", quality=92); media = "media.jpg"
    post = {"id": pid, "format": idea["format"], "caption": idea["caption"], "hashtags": idea["hashtags"], "media": media, "status": "pending"}
    json.dump(post, open(f"{d}/post.json", "w"), ensure_ascii=False, indent=1); tg_send(post, f"{d}/{media}")
