"""Генерира чернови: AI фотографии на рамката в стила на най-добрите кампании + студийни снимки + Reels. Праща ги в Telegram за одобрение."""
import os, json, random, subprocess, time, requests, glob, base64, io
from PIL import Image, ImageDraw
import design, studio

BRAND = os.environ.get("BRAND_NAME") or "OneOptic"
HANDLE = os.environ.get("IG_HANDLE") or "@oneoptic.bg"
N = int(os.environ.get("POSTS_PER_RUN") or "4")
AI_PER_RUN = int(os.environ.get("AI_PER_RUN") or "3")
MODEL = os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash"
IMG_MODEL = os.environ.get("GEMINI_IMAGE_MODEL") or "gemini-2.5-flash-image"
DRY = os.environ.get("DRY_RUN") == "1"
TG = f"https://api.telegram.org/bot{os.environ.get('TG_BOT_TOKEN', '')}"
CHAT = os.environ.get("TG_CHAT_ID", "")
GEM = "https://generativelanguage.googleapis.com/v1beta/models"

# Арт директории (само стил, написани по визуалните примери на клиента). Ключ: (кога е подходяща, описание за AI)
ART = {
    "mono_color": ("цветни или ярки рамки; монохромен портрет",
        "Monochrome colour-block fashion portrait: the subject, tailored coat, optional cap and the seamless backdrop all in ONE saturated hue (deep red, oxblood or cobalt), "
        "profile or three-quarter view, slicked-back or sleek bob hair, soft even studio light, glossy skin, very minimal and graphic."),
    "spotlight": ("тъмни, черни, дебели рамки; драматичен прожектор",
        "Dramatic spotlight portrait: saturated orange-to-red gradient backdrop with a hard circular pool of light and a soft shadow cast across the upper face and glasses, "
        "subject dressed in black with slicked-back hair, cinematic and moody, medium-format look, deep shadows."),
    "hands_tailoring": ("всякакви рамки; ръка и кроено облекло, много бял фон",
        "Minimal luxury still life with hands: pure white seamless backdrop, a hand in a tailored sleeve or black leather glove holding the glasses, or the glasses balanced on the knee "
        "of dark wool trousers, strong graphic negative space, crisp hard shadows, high-end campaign photograph."),
    "noir": ("черни или строги рамки; кино нуар",
        "Cinematic noir: near-black scene, one beam of light on a model in white tailoring, shallow depth of field, out-of-focus dark silhouettes in the foreground, glasses clearly lit."),
    "beauty_closeup": ("големи, овални, прозрачни рамки; близък план",
        "Tight beauty close-up: the face fills the frame, glossy wet-look slicked hair, a bold lip colour, the glasses large and tack sharp, clean light backdrop, crisp skin texture, high-fashion beauty photograph."),
    "stone_plinth": ("всякакви рамки; галерия",
        "Gallery still life: the glasses resting on a raw pale stone on a soft grey seamless backdrop, one soft key light, subtle contact shadow, tactile and minimal."),
    "magazine": ("костенурка, топли тонове, ацетат; настроение",
        "Moody lifestyle still life: the glasses lying beside an open fashion magazine on a rust-brown leather sofa, warm side light, fine film grain."),
    "full_body": ("смели рамки; цяла фигура",
        "Full-body studio fashion photograph: model in sharp black tailoring on a light grey seamless, long hard shadow on the wall, confident pose, glasses clearly visible."),
}


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


def gemini_text(prompt, imgs=()):
    if os.environ.get("MOCK_STYLE"): return os.environ["MOCK_STYLE"]
    r = requests.post(f"{GEM}/{MODEL}:generateContent", params={"key": gem_key()}, timeout=120,
                      json={"contents": [{"parts": [{"text": prompt}] + list(imgs)}]}).json()
    return r["candidates"][0]["content"]["parts"][0]["text"].strip()


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
        print("AI снимка: няма изображение в отговора", str(r)[:400])
    except Exception as e:
        print("AI снимка неуспешна:", str(e)[:400])
    return None


def finish_ai(im, size=(1080, 1350)):
    """Изрязва до 4:5 и добавя само малка марка отдолу (като при луксозните кампании)."""
    W, H = size; s = max(W / im.width, H / im.height); im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
    l, t = (im.width - W) // 2, (im.height - H) // 2; im = im.crop((l, t, l + W, t + H)).convert("RGBA")
    ov = Image.new("RGBA", size); d = ImageDraw.Draw(ov)
    for y in range(int(H * .88), H): d.line([(0, y), (W, y)], fill=(0, 0, 0, int(120 * (y - H * .88) / (H * .12))))
    im = Image.alpha_composite(im, ov); d = ImageDraw.Draw(im)
    design.spaced(d, (W // 2, H - int(H * .062)), BRAND.upper(), design.F("montserrat", W * .032, 600), (246, 242, 234), W * .012, "m")
    return im.convert("RGB")


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

    def zf(i, k):
        z = 1 + zoom * k / (per + trf); cw, ch = W / z, H / z; l, t = (W - cw) / 2, (H - ch) / 2
        return imgs[i].resize((W, H), Image.BILINEAR, box=(l, t, l + cw, t + ch))

    for n in range(total):
        i = min(n // per, len(imgs) - 1); k = n - i * per; fr = zf(i, k)
        if i + 1 < len(imgs) and k >= per - trf: fr = Image.blend(fr, zf(i + 1, k - (per - trf)), (k - (per - trf)) / trf)
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
STYLE = style_notes(ins)
brief = {"наши_най-добри": [(p.get("caption") or "")[:200] for p in ins["own_top"][:5]],
         "водещ_конкурент": best and {"акаунт": best["username"], "ER": best["avg_er"],
             "най-добри_постове": [{"тип": p["media_type"], "текст": (p.get("caption") or "")[:200]} for p in best["top_posts"][:5]]},
         "визуален_стил_на_най-добрите_постове": STYLE[:1200]}
dirs_help = "\n".join(f'- "{k}": {v[0]}' for k, v in ART.items())
prompt = f"""Ти си арт директор и social media мениджър на оптика "{BRAND}" (диоптрични и слънчеви очила) в България.
Визията е като при най-добрите луксозни кампании: ФОТОГРАФСКА, редакционна, много въздух, силна светлина, минимален текст. Никакви плочки и банери.
Какво работи при нас и при конкурентите: {json.dumps(brief, ensure_ascii=False)}
Научи СТРУКТУРАТА (кукичка, дължина, CTA), не копирай чужди текстове.
Тон: микс от луксозен и приятелски. Език: български. Без здравни обещания, без цени и отстъпки, без измислени модели или твърдения.
Приложени са снимките на очилата с имената на файловете. За всяка избрана снимка определи марката, ако се вижда на рамката (напр. "DSQUARED2", "Jimmy Choo", "Guess"), иначе "".
Върни JSON списък от {N} поста с РАЗЛИЧНИ снимки. Формати: "ai" (AI фотография на рамката; до {AI_PER_RUN} поста), "photo" (студийна снимка на самата рамка), "reel" (максимум 1; 3-4 снимки).
За "ai" избери "direction" според рамката: 
{dirs_help}
Всеки пост:
{{"format":"ai|photo|reel","brand":"марка или празно","tagline":"1-2 думи, напр. ИНТУИЦИЯ, ВНЕ ВРЕМЕНИ","caption":"копи с кукичка и CTA",
"hashtags":["8-12 хаштага"],"photos":["файл(ове)"],"reel_lines":["1-2 думи на кадър, само за reel"],
"direction":"ключ от списъка, само за ai","scene_desc":"само за ai, на английски: поза, облекло, обстановка, настроение; ВИНАГИ измислен ВЪЗРАСТЕН човек, не прилича на реален"}}"""
imgs = []
for p in random.sample(photos, min(len(photos), 12)):
    t = Image.open(p).convert("RGB"); t.thumbnail((512, 512)); buf = io.BytesIO(); t.save(buf, "JPEG", quality=80)
    imgs += [{"text": "Снимка, файл: " + os.path.basename(p)}, {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(buf.getvalue()).decode()}}]
ideas = [i for i in ask_gemini(prompt, imgs) if isinstance(i, dict) and i.get("caption")][:N]
assert ideas, "Gemini не върна валидни идеи"

ai_used = 0
for idea in ideas:
    fmt = idea.get("format", "photo"); fmt = "ai" if fmt in ("ai", "ai_model", "ai_scene") else (fmt if fmt in ("photo", "reel") else "photo")
    idea.setdefault("hashtags", []); brand = idea.get("brand", ""); tagline = idea.get("tagline") or idea.get("headline") or ""
    files = [f"products/{os.path.basename(x)}" for x in idea.get("photos", []) if os.path.exists(f"products/{os.path.basename(x)}")] or [random.choice(photos)]
    pid = time.strftime("%Y%m%d-%H%M%S") + f"-{random.randint(100,999)}"; d = f"queue/{pid}"; os.makedirs(d)
    ai = False; media = "media.jpg"

    if fmt == "ai" and ai_used < AI_PER_RUN:
        ai_used += 1
        direction = ART.get(idea.get("direction"), random.choice(list(ART.values())))[1]
        keep = ("Use the reference image: the glasses in the new photograph must be IDENTICAL to the reference frame - same shape, colour, proportions, temples and small details; "
                "never change, redraw or invent logos. The glasses are large, sharp and clearly visible. Premium luxury-campaign photograph, 4:5 portrait, natural realistic skin and hands, "
                "correct anatomy, no text, no watermark, no extra eyewear.")
        st = f" Visual style notes from top eyewear accounts (style only): {STYLE[:600]}" if STYLE else ""
        pr = f"{direction} {idea.get('scene_desc') or ''} Any person is an invented adult who does not resemble any real person.{st} {keep}"
        im = ai_image(pr, files[0])
        if im is not None:
            finish_ai(im).save(f"{d}/media.jpg", quality=93); ai = True
            idea["caption"] = idea["caption"].rstrip() + "\n\n✨ Визуалът е създаден с AI."
        else: fmt = "photo"; print("→ падам към студийна снимка")
    elif fmt == "ai": fmt = "photo"

    if not ai and fmt == "reel":
        prod0 = design.prep(files[0]); P = design.palette(brand, prod0); style = random.choice(list(studio.STYLES)); lines = idea.get("reel_lines") or []
        seed = random.randint(1, 10**6)
        for i, f in enumerate(files[:4]):
            line = (lines[i] if i < len(lines) and lines[i] else tagline) if i else tagline
            im, _ = studio.render_studio(f, (1080, 1920), brand=brand, store=BRAND, handle=HANDLE, tagline=line, style=style, P=P, seed=seed + i)
            im.save(f"{d}/f{i+1}.jpg", quality=93)
        nfr = len(files[:4])
        if nfr < 3:
            for j in range(nfr, 3):
                im, _ = studio.render_studio(files[0], (1080, 1920), brand=brand, store=BRAND, handle=HANDLE, tagline="Разгледай в магазина", style=random.choice(list(studio.STYLES)), P=P, seed=seed + j)
                im.save(f"{d}/f{j+1}.jpg", quality=93)
            nfr = 3
        make_reel([f"{d}/f{i+1}.jpg" for i in range(nfr)], f"{d}/media.mp4"); media = "media.mp4"
        for x in glob.glob(f"{d}/f*.jpg"): os.remove(x)
    elif not ai:
        fmt = "photo"; im, _ = studio.render_studio(files[0], (1080, 1350), brand=brand, store=BRAND, handle=HANDLE, tagline=tagline)
        im.save(f"{d}/media.jpg", quality=93)

    post = {"id": pid, "format": "reel" if media.endswith("mp4") else "photo", "ai": ai, "caption": idea["caption"], "hashtags": idea["hashtags"], "media": media, "status": "pending"}
    json.dump(post, open(f"{d}/post.json", "w"), ensure_ascii=False, indent=1); tg_send(post, f"{d}/{media}")
