"""Рекламен вид върху AI снимка: марка/лого, слоган и 'Нова колекция в <магазин>'. Текстът се слага от нас, за да е винаги вярен на кирилица."""
import os
from PIL import Image, ImageDraw
import design


def slug(s): return "".join(ch for ch in s.lower() if ch.isalnum())


def finish_ad(im, brand, slogan, layout="bottom", store="OneOptic", size=(1080, 1350)):
    """Рекламен вид: името/логото на марката, слоган и 'Нова колекция в <магазин>'. Текстът се слага от нас, за да е винаги правилен на кирилица."""
    W, H = size; s = max(W / im.width, H / im.height); im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
    l, t = (im.width - W) // 2, (im.height - H) // 2; im = im.crop((l, t, l + W, t + H)).convert("RGBA")
    ov = Image.new("RGBA", size); od = ImageDraw.Draw(ov)
    top = layout == "top"
    for y in range(H):  # мек тъмен градиент зад текста
        if top: a = int(150 * max(0, 1 - y / (H * .42)))
        else: a = int(185 * max(0, (y - H * .5) / (H * .5)))
        a = max(a, int(110 * max(0, (y - H * .86) / (H * .14))))
        if a: od.line([(0, y), (W, y)], fill=(8, 6, 4, a))
    im = Image.alpha_composite(im, ov); d = ImageDraw.Draw(im)
    cx = W // 2; y0 = int(H * (.075 if top else .70)); white = (250, 247, 240)
    logo_path = f"logos/{slug(brand)}.png" if brand else ""
    if logo_path and os.path.exists(logo_path):   # официално лого, ако е добавено в папка logos/
        lg = Image.open(logo_path).convert("RGBA"); k = (W * .62) / lg.width; lg = lg.resize((int(lg.width * k), int(lg.height * k)), Image.LANCZOS)
        im.alpha_composite(lg, (cx - lg.width // 2, y0)); y = y0 + lg.height + int(H * .02)
    elif brand:
        name = brand.upper(); f = design.F("cormorant", 100, 600); k = (W * .74) / max(sum(f.getlength(c) + 6 for c in name), 1)
        f = design.F("cormorant", min(100 * k, W * .16), 600); tw = design.spaced(d, (cx, y0), name, f, white, f.size * .05, "m"); y = y0 + int(f.size * 1.25)
    else: y = y0
    if slogan:
        sf = design.F("montserrat", W * .024, 400); lines = design.wrap(slogan.upper(), sf, W * .62)[:3]
        for ln in lines:
            design.spaced(d, (cx, y), ln, sf, white, W * .004, "m"); y += int(W * .034)
    d.line([cx - W * .11, H - int(H * .105), cx + W * .11, H - int(H * .105)], fill=(235, 225, 205), width=1)
    design.spaced(d, (cx, H - int(H * .092)), "НОВА КОЛЕКЦИЯ В", design.F("montserrat", W * .014, 500), (225, 218, 205), W * .004, "m")
    design.spaced(d, (cx, H - int(H * .072)), store.upper(), design.F("montserrat", W * .028, 500), white, W * .012, "m")
    return im.convert("RGB")
