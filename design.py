"""Дизайнерски шаблони за постове: оформление, цветове и шрифтове според марката на очилата."""
import os, random, colorsys, textwrap
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageFilter

FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
FONTS = {  # име: (файл, тегло по подразбиране)
    "playfair": ("Playfair.ttf", 700), "playfair_i": ("PlayfairItalic.ttf", 500),
    "cormorant": ("Cormorant.ttf", 500), "cormorant_i": ("CormorantItalic.ttf", 500),
    "montserrat": ("Montserrat.ttf", 400), "oswald": ("Oswald.ttf", 600), "unbounded": ("Unbounded.ttf", 500),
}
GOLD = (201, 164, 92)

# Профили на марките: кои шаблони им отиват, палитра и шрифт за заглавията
BRANDS = {
    "dsquared": dict(label="DSQUARED²", templates=["bold", "editorial"], bg=(15, 15, 15), panel=(231, 227, 219),
                     ink=(15, 15, 15), light=(244, 241, 235), accent=(222, 52, 40), head="oswald", headw=600, upper=True),
    "jimmy choo": dict(label="JIMMY CHOO", templates=["arch", "circle"], bg=(240, 224, 216), panel=(231, 203, 190),
                       ink=(58, 38, 38), light=(250, 243, 238), accent=(176, 132, 62), head="playfair_i", headw=500, upper=False),
    "guess": dict(label="GUESS", templates=["circle", "bold"], bg=(17, 15, 13), panel=(214, 178, 106),
                  ink=(17, 15, 13), light=(247, 240, 226), accent=GOLD, head="unbounded", headw=500, upper=True),
    "zegna": dict(label="ZEGNA", templates=["arch", "editorial"], bg=(222, 214, 200), panel=(200, 190, 172),
                  ink=(40, 38, 32), light=(246, 242, 234), accent=(104, 102, 62), head="cormorant_i", headw=500, upper=False),
}


def F(name, size, w=None):
    fn, dw = FONTS[name]
    f = ImageFont.truetype(os.path.join(FD, fn), max(8, int(size)))
    try: f.set_variation_by_axes([w or dw])
    except Exception: pass
    return f


def lum(c): return (0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]) / 255
def mix(a, b, t): return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))
def hsv(h, s, v): return tuple(int(x * 255) for x in colorsys.hsv_to_rgb(h, s, v))


def spaced(d, xy, text, font, fill, track=0, anchor="l"):
    w = sum(font.getlength(ch) for ch in text) + track * (len(text) - 1)
    x, y = xy
    if anchor == "m": x -= w / 2
    elif anchor == "r": x -= w
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill); x += font.getlength(ch) + track
    return w


def wrap(text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if font.getlength(t) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines


def fit(text, name, w, maxw, maxh, start, minsize, maxlines, lh=1.12):
    s = start
    while True:
        f = F(name, s, w); lines = wrap(text, f, maxw)
        ok = len(lines) <= maxlines and all(f.getlength(l) <= maxw for l in lines) and len(lines) * s * lh <= maxh
        if ok or s <= minsize: return f, lines, s
        s -= 4


def draw_lines(d, lines, font, size, x, y, fill, anchor="l", lh=1.12):
    for l in lines:
        d.text((x, y), l, font=font, fill=fill, anchor={"l": "la", "m": "ma", "r": "ra"}[anchor]); y += size * lh
    return y + size * .18


def pill(d, x, y, text, font, fill, fg, pad=None):
    pad = pad or font.size * .7
    w = font.getlength(text) + pad * 2 + font.size * .12 * len(text); h = font.size * 2.0
    d.rounded_rectangle([x, y, x + w, y + h], radius=h / 2, fill=fill)
    spaced(d, (x + pad, y + h / 2 - font.size * .62), text, font, fg, font.size * .12)
    return w, h


def arch(d, x, y, w, h, fill=None, outline=None, width=2):
    r = w // 2
    if fill:
        d.ellipse([x, y, x + w, y + w], fill=fill); d.rectangle([x, y + r, x + w, y + h], fill=fill)
    if outline:
        d.arc([x, y, x + w, y + w], 180, 360, fill=outline, width=width)
        d.line([x, y + r, x, y + h], fill=outline, width=width); d.line([x + w, y + r, x + w, y + h], fill=outline, width=width)
        d.line([x, y + h, x + w, y + h], fill=outline, width=width)


# ---------- продуктова снимка ----------
def prep(photo):
    im = Image.open(photo).convert("RGB"); bw, bh = im.size; px = im.load()
    edge = [px[x, y] for x in range(0, bw, max(1, bw // 40)) for y in (0, bh - 1)] + \
           [px[x, y] for y in range(0, bh, max(1, bh // 40)) for x in (0, bw - 1)]
    bg = [sorted(c[i] for c in edge)[len(edge) // 2] for i in range(3)]
    if min(bg) > 150:
        im = Image.merge("RGB", [ch.point(lambda v, b=b: min(255, int(v * 255 / max(b, 1)))) for ch, b in zip(im.split(), bg)])
    im = im.point(lambda v: 255 if v > 243 else v)
    box = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).convert("L").point(lambda p: 255 if p > 30 else 0).getbbox()
    if box:
        pad = int(max(box[2] - box[0], box[3] - box[1]) * .03)
        im = im.crop((max(0, box[0] - pad), max(0, box[1] - pad), min(bw, box[2] + pad), min(bh, box[3] + pad)))
    return im


def frame_color(prod):
    """Цветът на рамката: (hue, насоченост) или None за черни/сиви/метални."""
    sm = prod.resize((64, 64)); sat = []
    for r, g, b in sm.getdata():
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if min(r, g, b) < 215 and v > .18: sat.append((h, s, v))
    if not sat: return None
    strong = [x for x in sat if x[1] > .40]
    if len(strong) / len(sat) < .10: return None
    return sum(x[0] for x in strong) / len(strong)


def palette(brand_text, prod):
    b = (brand_text or "").lower()
    for k, p in BRANDS.items():
        if k in b: return dict(p)
    h = frame_color(prod)
    if h is not None:
        return dict(label="", templates=["circle", "arch", "editorial"], bg=hsv(h, .62, .27), panel=hsv(h, .10, .96),
                    ink=hsv(h, .5, .16), light=hsv(h, .05, .98), accent=GOLD, head="playfair_i", headw=500, upper=False)
    return dict(label="", templates=["arch", "editorial", "circle"], bg=(26, 24, 22), panel=(234, 229, 219), ink=(26, 24, 22),
                light=(246, 242, 234), accent=GOLD, head="cormorant_i", headw=500, upper=False)


def place(c, prod, cx, cy, maxw, maxh, shadow=True):
    k = min(maxw / prod.width, maxh / prod.height, 2.4)
    p = prod.resize((max(1, int(prod.width * k)), max(1, int(prod.height * k))), Image.LANCZOS)
    x0, y0 = int(cx - p.width / 2), int(cy - p.height / 2)
    if shadow:
        sh = Image.new("L", c.size, 0); sd = ImageDraw.Draw(sh)
        sw, shh = p.width * .78, max(10, c.height * .012)
        sy = y0 + p.height + c.height * .012
        sd.ellipse([cx - sw / 2, sy - shh, cx + sw / 2, sy + shh], fill=70)
        sh = sh.filter(ImageFilter.GaussianBlur(c.height * .010))
        c.paste(Image.new("RGB", c.size, (0, 0, 0)), (0, 0), sh)
    box = (x0, y0, x0 + p.width, y0 + p.height)
    c.paste(ImageChops.multiply(c.crop(box), p), box)


def grain(c, amt=.035):
    n = Image.effect_noise(c.size, 28).convert("RGB")
    return Image.blend(c, ImageChops.overlay(c, n), amt * 4)


def head_text(P, s): return s.upper() if P["upper"] else s


# ---------- шаблони ----------
def t_arch(W, H, P, prod, T):
    c = Image.new("RGB", (W, H), P["bg"]); d = ImageDraw.Draw(c)
    tx = P["light"] if lum(P["bg"]) < .5 else P["ink"]; m = int(W * .07); tall = H / W > 1.5
    spaced(d, (W // 2, int(H * .045)), P["label"] or T["store"], F("montserrat", W * .024, 600), tx, W * .010, "m")
    aw, ah, ay = int(W * .74), int(H * (.40 if tall else .46)), int(H * (.095 if tall else .105)); ax = (W - aw) // 2
    arch(d, ax - 22, ay - 22, aw + 44, ah + 44, outline=mix(P["accent"], P["bg"], .15), width=2)
    arch(d, ax, ay, aw, ah, fill=P["panel"])
    place(c, prod, W // 2, ay + int(ah * .60), int(aw * .88), int(ah * .40))
    spaced(d, (W // 2, ay + int(ah * .90)), T["tag"], F("montserrat", W * .019, 600), mix(P["ink"], P["panel"], .30), W * .008, "m")
    y = ay + ah + int(H * .05)
    f, lines, s = fit(head_text(P, T["headline"]), P["head"], P["headw"], W * .84, H * .17, W * .105, W * .06, 3)
    y = draw_lines(d, lines, f, s, W // 2, y, P["light"] if lum(P["bg"]) < .5 else P["ink"], "m")
    if T["sub"]:
        fs = F("montserrat", W * .027, 300); sl = wrap(T["sub"], fs, W * .70)[:3]
        draw_lines(d, sl, fs, W * .027, W // 2, y + H * .012, mix(tx, P["bg"], .22), "m", 1.45)
    d.line([W // 2 - W * .05, H - H * .075, W // 2 + W * .05, H - H * .075], fill=P["accent"], width=2)
    spaced(d, (W // 2, H - int(H * .06)), T["handle"].upper(), F("montserrat", W * .021, 500), mix(tx, P["bg"], .3), W * .006, "m")
    return c


def t_circle(W, H, P, prod, T):
    c = Image.new("RGB", (W, H), P["bg"]); d = ImageDraw.Draw(c)
    tx = P["light"] if lum(P["bg"]) < .5 else P["ink"]; m = int(W * .08)
    f, lines, s = fit(head_text(P, T["headline"]), P["head"], P["headw"], W * .84, H * .16, W * .088, W * .05, 3)
    y = int(H * .085) + int(W * .02)
    spaced(d, (m, int(H * .05)), (P["label"] or T["store"]), F("montserrat", W * .022, 600), P["accent"], W * .009)
    y = draw_lines(d, lines, f, s, m, y, tx, "l")
    fs = F("montserrat", W * .025, 300)
    if T["sub"]: y = draw_lines(d, wrap(T["sub"], fs, W * .70)[:2], fs, W * .025, m, y + H * .004, mix(tx, P["bg"], .22), "l", 1.4)
    room_bottom = H - int(H * .15)
    R = int(min(W * .34, (room_bottom - y - H * .02) / 2)); cy = int(y + H * .02 + R)
    for i, k in enumerate([1.10, 1.21]):
        r = int(R * k); d.ellipse([W // 2 - r, cy - r, W // 2 + r, cy + r], outline=mix(P["accent"], P["bg"], .60 + i * .15), width=2)
    d.ellipse([W // 2 - R, cy - R, W // 2 + R, cy + R], fill=P["panel"])
    place(c, prod, W // 2, cy, int(R * 1.62), int(R * .95))
    pf = F("montserrat", W * .021, 600); pill(d, m, H - int(H * .105), T["tag"], pf, P["accent"], P["ink"] if lum(P["accent"]) > .5 else P["light"])
    spaced(d, (W - m, H - int(H * .068)), T["handle"].upper(), F("montserrat", W * .02, 500), mix(tx, P["bg"], .35), W * .006, "r")
    return c


def t_bold(W, H, P, prod, T):
    light_bg = P["panel"]; c = Image.new("RGB", (W, H), light_bg); d = ImageDraw.Draw(c)
    tone = mix(light_bg, (0, 0, 0), .09); name = (P["label"] or T["store"]).upper()
    tall = H / W > 1.5; zone = int(H * (.64 if tall else .68))
    f = F("oswald", 100, 700); k = (W * .98) / max(f.getlength(name), 1); f = F("oswald", min(100 * k, W * .5), 700)
    for i, yy in enumerate([int(H * .05), int(H * .05) + int(f.size * .92), int(H * .05) + int(f.size * 1.84)]):
        if yy + f.size * .6 < zone: d.text((W // 2, yy), name, font=f, fill=tone if i != 1 else mix(light_bg, P["accent"], .14), anchor="ma")
    place(c, prod, W // 2, int(zone * .52), int(W * .94), int(zone * .5))
    d.rectangle([0, zone, W, H], fill=P["ink"]); d.rectangle([0, zone, W, zone + 8], fill=P["accent"])
    m = int(W * .07); pf = F("montserrat", W * .021, 600)
    pill(d, m, zone + int(H * .03), T["tag"], pf, P["accent"], P["light"])
    f2, lines, s = fit(head_text(P, T["headline"]), P["head"], P["headw"], W * .86, H * .15, W * .10, W * .055, 3, 1.02)
    y = draw_lines(d, lines, f2, s, m, zone + int(H * .095), P["light"], "l", 1.02)
    fs = F("montserrat", W * .025, 300); draw_lines(d, wrap(T["sub"], fs, W * .62)[:2], fs, W * .025, m, y + H * .008, mix(P["light"], P["ink"], .3), "l", 1.4)
    spaced(d, (W - m, H - int(H * .05)), T["handle"].upper(), F("montserrat", W * .02, 500), mix(P["light"], P["ink"], .45), W * .006, "r")
    return c


def t_editorial(W, H, P, prod, T):
    c = Image.new("RGB", (W, H), P["bg"]); d = ImageDraw.Draw(c); tall = H / W > 1.5
    zone = int(H * (.66 if tall else .64)); inset = int(W * .035)
    d.rectangle([0, 0, W, zone], fill=P["panel"])
    d.rectangle([inset, inset, W - inset, zone - inset], outline=mix(P["ink"], P["panel"], .55), width=2)
    place(c, prod, W // 2, int(zone * .52), int(W * (.86 if tall else .78)), int(zone * (.52 if tall else .46)))
    pf = F("montserrat", W * .02, 600); pill(d, int(W * .07), int(W * .07), T["tag"], pf, P["ink"], P["light"])
    vt = (P["label"] or T["store"]).upper(); vf = F("montserrat", W * .021, 600)
    tw = int(sum(vf.getlength(ch) for ch in vt) + W * .012 * len(vt)); layer = Image.new("RGBA", (tw + 10, int(W * .04)), (0, 0, 0, 0))
    spaced(ImageDraw.Draw(layer), (0, 0), vt, vf, mix(P["ink"], P["panel"], .2) + (255,), W * .012)
    layer = layer.rotate(90, expand=True); c.paste(layer, (int(W * .07), zone - layer.height - int(W * .07)), layer)
    m = int(W * .07); tx = P["light"] if lum(P["bg"]) < .5 else P["ink"]
    f, lines, s = fit(head_text(P, T["headline"]), P["head"], P["headw"], W * .86, H * (.20 if tall else .17), W * (.13 if tall else .10), W * .055, 3)
    y = draw_lines(d, lines, f, s, m, zone + int(H * .04), tx, "l")
    fs = F("montserrat", W * .026, 300); y = draw_lines(d, wrap(T["sub"], fs, W * .66)[:2], fs, W * .026, m, y + H * .01, mix(tx, P["bg"], .25), "l", 1.45)
    d.line([m, H - int(H * .085), W - m, H - int(H * .085)], fill=mix(tx, P["bg"], .7), width=1)
    spaced(d, (m, H - int(H * .06)), T["store"].upper(), F("montserrat", W * .02, 600), P["accent"], W * .006)
    spaced(d, (W - m, H - int(H * .06)), T["handle"].upper(), F("montserrat", W * .02, 500), mix(tx, P["bg"], .35), W * .006, "r")
    return c


TEMPLATES = {"arch": t_arch, "circle": t_circle, "bold": t_bold, "editorial": t_editorial}


def render_post(photo, text, size, brand="", store="", handle="", tag="", sub="", template=None, P=None, prod=None):
    """Връща готова картинка. P/prod могат да се подадат, за да са еднакви между кадрите на Reel."""
    prod = prod or prep(photo); P = P or palette(brand, prod)
    tpl = template or random.choice(P["templates"])
    T = dict(headline=text, sub=sub, tag=tag or "НОВА КОЛЕКЦИЯ", store=store, handle=handle)
    return grain(TEMPLATES[tpl](size[0], size[1], P, prod, T)), P, tpl
