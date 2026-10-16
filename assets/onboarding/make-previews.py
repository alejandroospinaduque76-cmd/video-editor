# Generates the empezar caption-style previews (neutral abstract background, no people).
import math, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont
K = Path(sys.argv[1]); OUT = K / "assets/onboarding"; F = K / "assets/fonts"
W, H = 540, 960; S = W / 1080  # preview scale vs a 1080x1920 frame

def font(name, px): return ImageFont.truetype(str(F / name), int(round(px)))

def background(seed):
    top, bot = [(44, 52, 92), (30, 70, 78), (70, 44, 80)][seed], [(18, 20, 30), (12, 26, 30), (26, 16, 30)][seed]
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / (H - 1)
        d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bot)))
    blobs = Image.new("RGBA", (W, H), (0, 0, 0, 0)); bd = ImageDraw.Draw(blobs)
    for i, (cx, cy, r, col) in enumerate([(0.25, 0.28, 190, (120, 140, 255, 90)), (0.8, 0.45, 230, (255, 150, 120, 70)),
                                          (0.4, 0.75, 210, (90, 220, 200, 60))]):
        cx = (cx + 0.07 * seed * (i - 1)) % 1
        bd.ellipse([cx * W - r, cy * H - r, cx * W + r, cy * H + r], fill=col)
    blobs = blobs.filter(ImageFilter.GaussianBlur(70))
    im = Image.alpha_composite(im.convert("RGBA"), blobs)
    # a soft "subject" placeholder: abstract rounded shape, clearly not a person
    ph = Image.new("RGBA", (W, H), (0, 0, 0, 0)); pd = ImageDraw.Draw(ph)
    pd.rounded_rectangle([W * 0.2, H * 0.22, W * 0.8, H * 0.58], radius=40, fill=(255, 255, 255, 22),
                         outline=(255, 255, 255, 50), width=2)
    return Image.alpha_composite(im, ph)

def label(im, letter, name, desc):
    d = ImageDraw.Draw(im)
    f1, f2 = font("Inter-Black.otf", 30), font("Inter-Regular.otf", 17)
    d.rounded_rectangle([20, 20, 20 + 52, 72], radius=14, fill=(255, 255, 255, 235))
    d.text((46, 46), letter, font=f1, fill=(20, 20, 24), anchor="mm")
    d.text((86, 30), name, font=font("Inter-Bold.otf", 22), fill="white")
    d.text((86, 56), desc, font=f2, fill=(230, 230, 235))

def caja(im, text, y, px):
    d = ImageDraw.Draw(im); f = font("Inter-Bold.otf", px * S)
    x0, y0, x1, y1 = d.textbbox((W / 2, y * H), text, font=f, anchor="mm")
    padx, pady = 16, 10
    d.rounded_rectangle([x0 - padx, y0 - pady, x1 + padx, y1 + pady], radius=12, fill=(0, 0, 0, 235))
    d.text((W / 2, y * H), text, font=f, fill="white", anchor="mm")

def borde(im, words, y, px, colors, stroke):
    d = ImageDraw.Draw(im); f = font("Inter-Black.otf" if px > 60 else "Inter-Bold.otf", px * S)
    text = " ".join(words); total = d.textlength(text, font=f); sp = d.textlength(" ", font=f)
    x = W / 2 - total / 2
    for w, c in zip(words, colors):
        d.text((x, y * H), w, font=f, fill=c, anchor="lm", stroke_width=stroke, stroke_fill="black")
        x += d.textlength(w, font=f) + sp

A = background(0); caja(A, "así edito mis videos", 0.50, 49)
label(A, "A", "Caja", "texto blanco sobre caja negra")
B = background(1); borde(B, "así se ve mejor".split(), 0.78, 52, ["white"] * 4, 3)
label(B, "B", "Borde", "texto blanco con contorno negro")
C = background(2); borde(C, ["ESTO", "FUNCIONA"], 0.70, 84, ["white", "#ffd400"], 5)
label(C, "C", "Grande", "MAYÚSCULAS, 1–2 palabras, una resaltada")
for n, im in zip("ABC", (A, B, C)):
    im.convert("RGB").save(OUT / f"subtitulos-{n}.png", optimize=True)
G = 18
all_ = Image.new("RGB", (3 * W + 4 * G, H + 2 * G), (14, 14, 18))
for i, im in enumerate((A, B, C)):
    all_.paste(im.convert("RGB"), (G + i * (W + G), G))
all_.save(OUT / "subtitulos-ABC.png", optimize=True)
print("ok")
