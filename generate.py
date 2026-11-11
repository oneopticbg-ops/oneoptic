"""Генерира чернови (дизайнерска снимка / Reel / AI снимка) + копи на български и ги праща в Telegram за одобрение."""
import os, json, random, subprocess, time, requests, glob, base64, io
from PIL import Image
import design

BRAND = os.environ.get("BRAND_NAME") or "OneOptic"
HANDLE = os.environ.get("IG_HANDLE") or "@oneoptic.bg"
N = int(os.environ.get("POSTS_PER_RUN") or "4")
AI_PER_RUN = int(os.environ.get("AI_PER_RUN") or "2")
MODEL = os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash"
IMG_MODEL = os.environ.get("GEMINI_IMAGE_MODEL") or "gemini-2.5-flash-image"
DRY = os.environ.get("DRY_RUN") == "1"
TG = f"https://api.telegram.org/bot{os.environ.get('TG_BOT_TOKEN', '')}"
CHAT = os.environ.get("TG_CHAT_ID", "")
GEM = "https://generativelanguage.googleapis.com/v1beta/models"
TAGS = ["НОВА КОЛЕКЦИЯ", "ВЕЧЕ В МАГАЗИНА", "ИЗБОР НА СТИЛИСТА", "СТИЛ НА СЕЗОНА", "ЛИМИТИРАНА СЕРИЯ"]


def gem_key(): return os.environ.get("GEMINI_API_KEY", "")


def ask_gemini(prompt, imgs=()):
    if os.environ.get("MOCK_GEMINI"): return json.loads(os.environ["MOCK_GEMINI"])
    last = None
    for _ in range(3):
        try:
            r = requests.post(f"{GEM}/{MODEL}:generateContent", params={"key": gem_key()}, timeout=120,
                json={"contents": [{"parts": [{"text": prompt}] + list(imgs)}], "generationConfig": {"responseMimeType": "application/json"}})
            data = json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])
            if isinstance(data, dict): data = next((v for v in data.values() if isinstance(v, list)), [data])
            return data
        except Exception as e:
            last = e; time.sleep(5)
    raise RuntimeError(f"Gemini не отговори коректно: {last}")


def ai_image(prompt, ref_path):
    """AI снимка по референтна снимка на рамката. Връща PIL Image или None (ако няма квота/достъп)."""
    if os.environ.get("MOCK_IMAGE"): return Image.open(os.environ["MOCK_IMAGE"]).convert("RGB")
    try:
        t = Image.open(ref_path).convert("RGB"); t.thumbnail((1024, 1024)); buf = io.BytesIO(); t.save(buf, "JPEG", quality=90)
        parts = [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(buf.getvalue()).decode()}}]
        r = requests.post(f"{GEM}/{IMG_MODEL}:generateContent", params={"key": gem_key()}, timeout=180,
            json={"contents": [{"parts": parts}], "generationConfig": {"responseModalities": ["IMAGE"]}}).json()
        for p in r["candidates"][0]["content"]["parts"]:
            d = p.get("inlineData") or p.get("inline_data")
            if d: return Image.open(io.BytesIO(base64.b64decode(d["data"]))).convert("RGB")
        print("AI снимка: няма изображение в отговора", str(r)[:300])
    except Exception as e:
        print("AI снимка неуспешна:", str(e)[:300])
    return None


def finish_ai(im, size=(1080, 1350)):
    """Изрязва до 4:5 и добавя фин брандинг долу."""
    from PIL import ImageDraw, ImageFont
    W, H = size; s = max(W / im.width, H / im.height); im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
    l, t = (im.width - W) // 2, (im.height - H) // 2; im = im.crop((l, t, l + W, t + H)).convert("RGBA")
    ov = Image.new("RGBA", size); d = ImageDraw.Draw(ov)
    for y in range(int(H * .86), H): d.line([(0, y), (W, y)], fill=(0, 0, 0, int(150 * (y - H * .86) / (H * .14))))
    im = Image.alpha_composite(im, ov); d = ImageDraw.Draw(im)
    design.spaced(d, (int(W * .06), H - int(H * .05)), BRAND.upper(), design.F("montserrat", W * .021, 600), (240, 220, 170), W * .008)
    design.spaced(d, (W - int(W * .06), H - int(H * .05)), HANDLE.upper(), design.F("montserrat", W * .02, 500), (225, 225, 225), W * .006, "r")
    return im.convert("RGB")



ART = {
    "heritage": ("Art direction 'Heritage Cinema': timeless Italian film-still look, shot on 35mm film with fine grain, warm amber and deep shadow tones, "
                 "soft directional window light or golden hour, classic composition with generous negative space, understated and elegant, slightly desaturated, "
                 "confident cinematic gaze, classic tailoring wardrobe in camel, white and charcoal. Feeling of craftsmanship and heritage."),
    "sunwarm": ("Art direction 'Sun-Warm Colour': vibrant sun-drenched palette of terracotta, olive, ochre, sand and deep brown, playful editorial fashion photography, "
                "strong direct sunlight or hard flash with crisp shadows, bold single-colour backdrop, candid youthful energy, slightly retro music-video styling, "
                "natural but saturated skin tones, high contrast."),
}


def gemini_text(prompt, imgs=()):
    if os.environ.get("MOCK_STYLE"): return os.environ["MOCK_STYLE"]
    r = requests.post(f"{GEM}/{MODEL}:generateContent", params={"key": gem_key()}, timeout=120,
                      json={"contents": [{"parts": [{"text": prompt}] + list(imgs)}]}).json()
    return r["candidates"][0]["content"]["parts"][0]["text"].strip()


def style_notes(ins):
    """Обобщава визуалния стил на най-успешните снимки на конкурентите (само като текст, без копиране). Кешира се за 7 дни."""
    path = "data/style.json"
    try:
        c = json.load(open(path))
        if time.time() - c.get("ts", 0) < 7 * 86400: return c.get("text", "")
    except Exception: pass
    shots = []
    for comp in ins.get("competitors", [])[:4]:
        for p in comp.get("top_posts", [])[:3]:
            if p.get("media_type") in ("IMAGE", "CAROUSEL_ALBUM") and p.get("media_url"): shots.append(p["media_url"])
    parts = []
    for u in shots[:8]:
        try:
            im = Image.open(io.BytesIO(requests.get(u, timeout=30).content)).convert("RGB"); im.thumbnail((512, 512)); b = io.BytesIO(); im.save(b, "JPEG", quality=80)
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(b.getvalue()).decode()}})
        except Exception: pass
    if not parts and not os.environ.get("MOCK_STYLE"): return ""
    try:
        text = gemini_text("You are an art director. These are the best-performing Instagram posts of leading eyewear brands. In 6 sentences, describe their shared "
                           "visual style for a photographer: lighting, colour palette, composition and framing, how the glasses are shown (on a face, on a set, close-up), "
                           "retouching and mood. Describe STYLE ONLY: never describe or name specific people, and do not reproduce any specific image.", parts)
        json.dump({"ts": time.time(), "text": text}, open(path, "w"), ensure_ascii=False)
        return text
    except Exception as e:
        print("Анализ на стила неуспешен:", str(e)[:200]); return ""


def tg_send(post, media_path):
    if DRY: print("DRY_RUN: пропускам Telegram за", media_path); return
    kb = {"inline_keyboard": [[{"text": "✅ Одобри", "callback_data": f"a:{post['id']}"}, {"text": "❌ Откажи", "callback_data": f"r:{post['id']}"}]]}
    label = "AI" if post.get("ai") else post["format"]
    note = "\n⚠️ AI снимка: провери дали рамката съвпада с реалния модел." if post.get("ai") else ""
    cap = (f"[{label}] {post['caption']}\n\n{' '.join(post['hashtags'])}{note}")[:1000]
    kind, field = ("sendVideo", "video") if post["format"] == "reel" else ("sendPhoto", "photo")
    requests.post(f"{TG}/{kind}", data={"chat_id": CHAT, "caption": cap, "reply_markup": json.dumps(kb)}, files={field: open(media_path, "rb")}, timeout=300)


def make_reel(frames, out, fps=24, dur=3.0, tr=0.5, zoom=0.06):
    """Плавно приближение във всеки кадър и преливане между тях (смята се с Pillow, подава се на ffmpeg)."""
    W, H = 1080, 1920
    imgs = [Image.open(f).convert("RGB") for f in frames]
    per = int(dur * fps); trf = int(tr * fps); total = per * len(imgs) + trf
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps),
                           "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", out], stdin=subprocess.PIPE)

    def zf(i, k):  # кадър k от клип i с лек зуум
        z = 1 + zoom * k / (per + trf); cw, ch = W / z, H / z
        l, t = (W - cw) / 2, (H - ch) / 2
        return imgs[i].resize((W, H), Image.BILINEAR, box=(l, t, l + cw, t + ch))

    for n in range(total):
        i = min(n // per, len(imgs) - 1); k = n - i * per
        fr = zf(i, k)
        if i + 1 < len(imgs) and k >= per - trf:  # преливане към следващия клип
            fr = Image.blend(fr, zf(i + 1, k - (per - trf)), (k - (per - trf)) / trf)
        ff.stdin.write(fr.tobytes())
    ff.stdin.close(); ff.wait()


# ---------------- данни и подбор на снимки ----------------
ins = json.load(open("data/insights.json")) if os.path.exists("data/insights.json") else {"own_top": [], "competitors": []}
os.makedirs("queue", exist_ok=True); os.makedirs("data", exist_ok=True)
allp = [p for p in glob.glob("products/*") if p.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
assert allp, "Сложи продуктови снимки в папка products/"
good = [p for p in allp if min(Image.open(p).size) >= 700]
photos = good or allp
print(f"Снимки: {len(allp)}, достатъчно големи: {len(good)}")
best = ins["competitors"][0] if ins["competitors"] else None
brief = {"наши_най-добри": [(p.get("caption") or "")[:200] for p in ins["own_top"][:5]],
         "водещ_конкурент": best and {"акаунт": best["username"], "ER": best["avg_er"],
             "най-добри_постове": [{"тип": p["media_type"], "текст": (p.get("caption") or "")[:200]} for p in best["top_posts"][:5]]}}
STYLE = style_notes(ins)
brief["визуален_стил_на_най-добрите_постове"] = STYLE[:1200]
prompt = f"""Ти си арт директор и social media мениджър на оптика "{BRAND}" (диоптрични и слънчеви очила) в България.
Стилът е като на най-добрите дизайнери в оптиката в Pinterest: премиум, редакционен, чисти форми, силна типография, много въздух.
Какво работи при нас и при водещия конкурент: {json.dumps(brief, ensure_ascii=False)}
Научи СТРУКТУРАТА (кукичка, дължина, CTA), не копирай чужди текстове.
Тон: микс от луксозен и приятелски. Език: български. Без здравни обещания, без цени и отстъпки, без измислени модели или твърдения.
Приложени са снимките на очилата с имената на файловете. За всяка избрана снимка определи марката, ако се вижда на рамката (напр. "DSQUARED2", "Jimmy Choo", "Guess", "Zegna"), иначе "".
Върни JSON списък от {N} поста с РАЗЛИЧНИ снимки. Формати: "photo" (дизайнерска карта), "reel" (максимум 1; 3-4 снимки),
"ai_model" (AI модел, който носи рамката) и "ai_scene" (AI фотография на рамката в изграден дизайнерски сет). Общо до {AI_PER_RUN} AI поста, поне един от тях ai_model.
Избери "direction": "heritage" (класически, филмов, топли тонове; за костенурка, метал, злато, класика) или "sunwarm" (цветен, слънчев, закачлив; за ярки, едри, смели рамки).
Всеки пост:
{{"format":"photo|reel|ai_model|ai_scene","brand":"марка или празно","headline":"заглавие до 5 думи, силно и поетично","sub":"подзаглавие до 10 думи",
"tag":"един от {TAGS}","reel_lines":["до 4 думи на кадър, само за reel"],"caption":"копи с кукичка и CTA","hashtags":["8-12 хаштага"],
"photos":["файл(ове)"],"direction":"heritage|sunwarm","model_desc":"само за ai_model, на английски: измислен ВЪЗРАСТЕН човек (не прилича на реален), пол, възраст, стайлинг, обстановка, поза",
"scene_desc":"само за ai_scene, на английски: фон, повърхност, реквизит, светлина, цветове, подходящи за рамката"}}"""
imgs = []
for p in random.sample(photos, min(len(photos), 12)):
    t = Image.open(p).convert("RGB"); t.thumbnail((512, 512)); buf = io.BytesIO(); t.save(buf, "JPEG", quality=80)
    imgs += [{"text": "Снимка, файл: " + os.path.basename(p)}, {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(buf.getvalue()).decode()}}]
ideas = [i for i in ask_gemini(prompt, imgs) if isinstance(i, dict) and i.get("caption")][:N]
assert ideas, "Gemini не върна валидни идеи"

ai_used = 0
for idea in ideas:
    fmt = idea.get("format", "photo")
    fmt = fmt if fmt in ("photo", "reel", "ai_model", "ai_scene") else "photo"
    idea.setdefault("hashtags", []); head = idea.get("headline") or idea.get("overlay") or "Рамка с характер"
    sub = idea.get("sub", ""); brand = idea.get("brand", ""); tag = idea.get("tag") if idea.get("tag") in TAGS else random.choice(TAGS)
    files = [f"products/{os.path.basename(x)}" for x in idea.get("photos", []) if os.path.exists(f"products/{os.path.basename(x)}")] or [random.choice(photos)]
    pid = time.strftime("%Y%m%d-%H%M%S") + f"-{random.randint(100,999)}"; d = f"queue/{pid}"; os.makedirs(d)
    ai = False; media = "media.jpg"
    direction = ART.get(idea.get("direction"), random.choice(list(ART.values())))
    keep = ("Keep the eyeglasses IDENTICAL to the reference image: same frame shape, colour, proportions, temples and details; never change or invent logos. "
            "Glasses large, sharp and clearly visible. Premium editorial magazine quality, 4:5 portrait. No text, no watermark, no extra eyewear, no distortion.")
    st = f" Visual style notes from top eyewear accounts (style only): {STYLE[:600]}" if STYLE else ""

    if fmt in ("ai_model", "ai_scene") and ai_used < AI_PER_RUN:
        ai_used += 1
        if fmt == "ai_model":
            pr = (f"Photorealistic editorial fashion photograph of {idea.get('model_desc') or 'a stylish adult model'}, an invented adult who does not resemble any real person, "
                  f"wearing the exact eyeglasses from the reference image. {direction}{st} {keep} Natural realistic skin, face clearly visible.")
        else:
            pr = (f"Premium product photograph of the exact eyeglasses from the reference image placed in a designed set: {idea.get('scene_desc') or 'on a sculptural plinth with soft shadows'}. "
                  f"Tactile props chosen to match the frame colours, minimal composition with negative space, soft realistic contact shadow. {direction}{st} {keep}")
        im = ai_image(pr, files[0])
        if im is not None:
            finish_ai(im).save(f"{d}/media.jpg", quality=93); ai = True
            idea["caption"] = idea["caption"].rstrip() + "\n\n✨ Визуалът е създаден с AI."
        else: fmt = "photo"; print("→ падам към дизайнерска карта")
    elif fmt in ("ai_model", "ai_scene"): fmt = "photo"

    if not ai and fmt == "reel":
        prod0 = design.prep(files[0]); P = design.palette(brand, prod0); tpl = random.choice(P["templates"]); lines = idea.get("reel_lines") or []
        for i, f in enumerate(files[:4]):
            txt = (lines[i] if i < len(lines) and lines[i] else head) if i else head
            im, _, _ = design.render_post(f, txt, (1080, 1920), brand=brand, store=BRAND, handle=HANDLE, tag=tag, sub=sub if i == 0 else "", template=tpl, P=P, prod=prod0 if i == 0 else None)
            im.save(f"{d}/f{i+1}.jpg", quality=93)
        nfr = len(files[:4])
        if nfr < 3:  # Reel с малко снимки: повтаряме с други шаблони
            for j in range(nfr, 3):
                im, _, _ = design.render_post(files[0], "Разгледай още в магазина", (1080, 1920), brand=brand, store=BRAND, handle=HANDLE, tag=tag, template=random.choice(P["templates"]), P=P, prod=prod0)
                im.save(f"{d}/f{j+1}.jpg", quality=93)
            nfr = 3
        make_reel([f"{d}/f{i+1}.jpg" for i in range(nfr)], f"{d}/media.mp4"); media = "media.mp4"
        for x in glob.glob(f"{d}/f*.jpg"): os.remove(x)
    elif not ai:
        fmt = "photo"; im, _, _ = design.render_post(files[0], head, (1080, 1350), brand=brand, store=BRAND, handle=HANDLE, tag=tag, sub=sub)
        im.save(f"{d}/media.jpg", quality=93)

    post = {"id": pid, "format": "reel" if media.endswith("mp4") else "photo", "ai": ai, "caption": idea["caption"], "hashtags": idea["hashtags"], "media": media, "status": "pending"}
    json.dump(post, open(f"{d}/post.json", "w"), ensure_ascii=False, indent=1); tg_send(post, f"{d}/{media}")
