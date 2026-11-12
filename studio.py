"""Студийни снимки на самата рамка: светлина, остри сенки, фонове в цвят, минимален текст.
Резервен вариант, когато AI снимка не е налична. Без плочки, бутони и заглавия."""
import random, math
from PIL import Image, ImageDraw, ImageChops, ImageFilter
import design
from design import F, spaced, lum, mix

MONO = {  # наситени монохромни фонове (стенa) – като цветните кампании
    "oxblood": (118, 24, 28), "cobalt": (30, 56, 136), "forest": (28, 78, 58), "terracotta": (178, 88, 60),
    "mustard": (200, 150, 38), "chocolate": (66, 38, 28), "powder": (186, 204, 214), "ink": (24, 30, 52), "blush": (226, 190, 180),
}


def cutout(prod):
    """Прозрачна маска на рамката от снимка с бял фон (прозрачните лещи остават прозрачни)."""
    white = Image.new("RGB", prod.size, (255, 255, 255))
    r, g, b = ImageChops.difference(prod, white).split()
    a = ImageChops.lighter(ImageChops.lighter(r, g), b).point(lambda v: min(255, int(v * 3.4)))
    return a.filter(ImageFilter.GaussianBlur(.6))


def gradient(size, top, bottom):
    W, H = size
    col = Image.new("RGB", (1, H))
    for y in range(H): col.putpixel((0, y), mix(top, bottom, y / max(H - 1, 1)))
    return col.resize((W, H))


def radial(size, center, radius, inner, outer):
    W, H = size
    m = Image.radial_gradient("L").resize((int(radius * 2), int(radius * 2)))  # 0 в центъра → 255 по краищата
    layer = Image.new("L", size, 255); layer.paste(m, (int(center[0] - radius), int(center[1] - radius)))
    return Image.composite(Image.new("RGB", size, outer), Image.new("RGB", size, inner), layer)


def stone(size, base):
    n = Image.effect_noise(size, 60).convert("L").filter(ImageFilter.GaussianBlur(1.4))
    n2 = Image.effect_noise(size, 18).convert("L").filter(ImageFilter.GaussianBlur(5))
    t = ImageChops.add(ImageChops.multiply(n, Image.new("L", size, 90)), ImageChops.multiply(n2, Image.new("L", size, 90)))
    t = t.point(lambda v: int(v * .9 + 18)).convert("RGB")
    return ImageChops.multiply(Image.new("RGB", size, base), ImageChops.blend(t, Image.new("RGB", size, (255, 255, 255)), .35))


def place_item(prod, alpha, W, H, cx, cy, maxw, maxh, angle=0, bleed=1.0):
    k = min(maxw / prod.width, maxh / prod.height, 3.0) * bleed
    rgb = prod.resize((max(1, int(prod.width * k)), max(1, int(prod.height * k))), Image.LANCZOS)
    al = alpha.resize(rgb.size, Image.LANCZOS)
    if angle:
        rgb = rgb.rotate(angle, Image.BICUBIC, expand=True, fillcolor=(255, 255, 255)); al = al.rotate(angle, Image.BICUBIC, expand=True, fillcolor=0)
    layer = Image.new("RGB", (W, H), (255, 255, 255)); A = Image.new("L", (W, H), 0)
    pos = (int(cx - rgb.width / 2), int(cy - rgb.height / 2)); layer.paste(rgb, pos); A.paste(al, pos)
    return layer, A, pos, rgb.size


def cast_shadow(bg, A, dx, dy, blur, strength, tint=(0, 0, 0), shear=0.0):
    W, H = bg.size
    S = A.transform((W, H), Image.AFFINE, (1, shear, -dx - shear * H * .5, 0, 1, -dy), resample=Image.BICUBIC)
    S = S.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * strength))
    dark = ImageChops.multiply(bg, Image.new("RGB", (W, H), mix((255, 255, 255), tint, .85)))
    return Image.composite(dark, bg, S)


def light_bars(size, angle, n=3, width=.16, gap=.10, soft=14, base=.35):
    """Маска на светлина през прозорец/решетка – наклонени ивици."""
    W, H = size
    big = Image.new("L", (W * 2, H * 2), 0); d = ImageDraw.Draw(big)
    for i in range(n):
        x = W * .3 + i * W * (width + gap)
        d.rectangle([x, -H, x + W * width, H * 3], fill=255)
    big = big.rotate(angle, Image.BICUBIC, center=(W, H)).crop((W // 2, H // 2, W // 2 + W, H // 2 + H)).filter(ImageFilter.GaussianBlur(soft))
    return big.point(lambda v: int(255 * base + v * (1 - base)))


def wordmark(c, P, brand, store, handle, tagline, dark):
    W, H = c.size; d = ImageDraw.Draw(c); fg = (246, 242, 234) if dark else (22, 20, 18); soft = mix(fg, (128, 128, 128), .35)
    name = (brand or store).upper()
    spaced(d, (W // 2, int(H * .905)), name, F("montserrat", W * .034, 600), fg, W * .012, "m")
    if tagline: spaced(d, (W // 2, int(H * .945)), tagline.upper(), F("montserrat", W * .017, 500), soft, W * .009, "m")
    spaced(d, (W // 2, int(H * .968)), handle.upper(), F("montserrat", W * .013, 400), soft, W * .006, "m") if not tagline else None


# ---------- стилове ----------
def s_seamless(W, H, prod, A, rnd, P):
    """Светъл безшевен фон + дълга остра сянка (като кампаниите с бял фон)."""
    top, bot = (244, 244, 242), (214, 214, 212)
    bg = gradient((W, H), top, bot)
    layer, Am, pos, sz = place_item(prod, A, W, H, W * (.5 + rnd.uniform(-.04, .04)), H * .46, W * .92, H * .42, rnd.uniform(-9, 9), 1.0)
    bg = cast_shadow(bg, Am, W * .07, H * .035, 5, .55, shear=.18)
    bg = cast_shadow(bg, Am, W * .015, H * .012, 18, .35)
    bg.paste(layer, (0, 0), Am); return bg, False


def s_mono(W, H, prod, A, rnd, P):
    """Монохромен цветен фон (стена + под), рамката в центъра, мека сянка."""
    name = rnd.choice(list(MONO)); wall = MONO[name]; floor = mix(wall, (0, 0, 0), .22)
    bg = Image.new("RGB", (W, H), wall); d = ImageDraw.Draw(bg); hy = int(H * .66)
    bg.paste(gradient((W, H - hy), mix(floor, wall, .25), floor), (0, hy))
    bg = Image.blend(bg, radial((W, H), (W * .35, H * .25), W * .9, mix(wall, (255, 255, 255), .16), mix(wall, (0, 0, 0), .35)), .55)
    layer, Am, pos, sz = place_item(prod, A, W, H, W * .5, H * .5, W * .9, H * .4, rnd.uniform(-6, 6), 1.0)
    bg = cast_shadow(bg, Am, W * .04, H * .03, 14, .55, tint=mix(wall, (0, 0, 0), .5))
    bg.paste(layer, (0, 0), Am); return bg, lum(wall) < .55


def s_spot(W, H, prod, A, rnd, P):
    """Прожектор: цветен градиент, твърд кръг светлина и сянка от решетка през рамката."""
    glow = rnd.choice([(236, 92, 40), (214, 40, 36), (240, 160, 50), (60, 110, 220)]); dark = mix(glow, (0, 0, 0), .78)
    bg = radial((W, H), (W * .5, H * .44), W * .85, glow, dark)
    d = ImageDraw.Draw(bg); R = int(W * .36)
    ring = Image.new("L", (W, H), 0); ImageDraw.Draw(ring).ellipse([W // 2 - R, int(H * .44) - R, W // 2 + R, int(H * .44) + R], fill=70)
    bg = Image.composite(Image.new("RGB", (W, H), mix(glow, (255, 220, 170), .35)), bg, ring.filter(ImageFilter.GaussianBlur(10)))
    layer, Am, pos, sz = place_item(prod, A, W, H, W * .5, H * .44, W * .86, H * .36, rnd.uniform(-5, 5), 1.0)
    bg = cast_shadow(bg, Am, W * .05, H * .04, 10, .7, tint=(0, 0, 0))
    bg.paste(layer, (0, 0), Am)
    lm = light_bars((W, H), rnd.choice([-24, 24, 32]), 3, .13, .09, 12, .38); bg = ImageChops.multiply(bg, Image.merge("RGB", [lm] * 3).point(lambda v: v))
    return bg, True


def s_plinth(W, H, prod, A, rnd, P):
    """Галерия: рамка, стъпила върху суров камък на меко сиво-бежово стенно платно."""
    tone = rnd.choice([(206, 200, 192), (196, 196, 198), (214, 204, 190)])
    bg = gradient((W, H), mix(tone, (255, 255, 255), .35), mix(tone, (0, 0, 0), .12))
    bw, bh, topH = int(W * .54), int(H * .21), int(H * .03); bx, by = (W - bw) // 2, int(H * .62)
    block = stone((bw, bh), mix(tone, (255, 255, 255), .25)); top = stone((bw, topH), mix(tone, (255, 255, 255), .55))
    sh = Image.new("L", (W, H), 0); ImageDraw.Draw(sh).rectangle([bx + int(W * .015), by, bx + bw + int(W * .06), by + bh + int(H * .015)], fill=255)
    bg = Image.composite(ImageChops.multiply(bg, Image.new("RGB", (W, H), (150, 148, 144))), bg, sh.filter(ImageFilter.GaussianBlur(24)).point(lambda v: int(v * .5)))
    bg.paste(block, (bx, by)); bg.paste(top, (bx, by - topH))
    k = min(W * .5 / prod.width, H * .2 / prod.height, 3.0); ih = prod.height * k
    layer, Am, pos, sz = place_item(prod, A, W, H, W * .5, by - topH * .45 - ih / 2, W * .5, H * .2, rnd.uniform(-3, 3), 1.0)
    bg = cast_shadow(bg, Am, W * .015, H * .008, 7, .6)
    bg.paste(layer, (0, 0), Am); return bg, False


STYLES = {"seamless": s_seamless, "mono": s_mono, "spot": s_spot, "plinth": s_plinth}


def render_studio(photo, size, brand="", store="", handle="", tagline="", style=None, P=None, prod=None, seed=None):
    rnd = random.Random(seed)
    prod = prod or design.prep(photo); P = P or design.palette(brand, prod)
    A = cutout(prod); W, H = size
    style = style or rnd.choice(list(STYLES))
    c, dark = STYLES[style](W, H, prod, A, rnd, P)
    c = c.convert("RGB"); wordmark(c, P, brand, store, handle, tagline, dark)
    return design.grain(c, .03), style
