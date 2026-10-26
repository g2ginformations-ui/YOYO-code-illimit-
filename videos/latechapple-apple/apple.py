"""La tech Apple 2K25 — motion design « keynote » : fond clair, grand texte noir, une touche de rouge, 60 i/s.

Usage : python3 apple.py <voix.wav> <dossier_polices> <sortie.mp4> [--stills t1,...] [--timeline f.json]
Les instants des mots viennent de mots.json ; le son de out/mix.wav (synth_apple.py).
"""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ICI))
from tag_marque import PLACES, PERIODE, HANDLE, NOM  # nom d'utilisateur (videos/marque.json)

VOIX, POLICES, SORTIE = sys.argv[1], sys.argv[2], sys.argv[3]
STILLS = [float(x) for x in sys.argv[sys.argv.index("--stills") + 1].split(",")] if "--stills" in sys.argv else None

W, H, FPS = 1080, 1920, 60
CX = 520  # axe de la zone sûre TikTok (x 120 à 920, y 280 à 1440)
BG, INK, GRIS, ROUGE, BLANC = (245, 245, 247), (29, 29, 31), (134, 134, 139), (232, 38, 43), (255, 255, 255)
FIN_HOLD = 1.7

with wave.open(VOIX) as wf:
    FIN_VOIX = wf.getnframes() / wf.getframerate()
DUREE = FIN_VOIX + FIN_HOLD
NF = int(round(DUREE * FPS))
MOTS = [{"t": w["text"], "s": w["start"], "e": w["end"]} for w in json.load(open(os.path.join(ICI, "mots.json")))["words"] if w["type"] == "word"]
def at(txt, n=1):
    k = 0
    for m in MOTS:
        if m["t"].lower().strip(".,?!:").startswith(txt.lower()):
            k += 1
            if k == n:
                return m["s"]
    raise KeyError(txt)

# ---------- courbes ----------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))
def prog(t, t0, d):
    return clamp((t - t0) / d)
def out_expo(p):
    return 1.0 if p >= 1 else 1 - 2 ** (-10 * p)
def out_cubic(p):
    return 1 - (1 - p) ** 3
def in_out(p):
    return 3 * p * p - 2 * p ** 3
def ressort(t, t0, freq=2.6, amort=8.0):
    x = t - t0
    return 0.0 if x <= 0 else 1 - math.exp(-amort * x) * math.cos(2 * math.pi * freq * x)

# ---------- textes, formes ----------
_f, _c = {}, {}
def police(poids, taille):
    k = (poids, taille)
    if k not in _f:
        _f[k] = ImageFont.truetype(os.path.join(POLICES, f"poppins-latin-{poids}-normal.woff"), taille)
    return _f[k]
def texte(txt, taille, col=INK, poids=900, max_l=800):
    k = ("t", txt, taille, col, poids, max_l)
    if k not in _c:
        f = police(poids, taille)
        while f.getlength(txt) > max_l and taille > 16:
            taille -= 2
            f = police(poids, taille)
        bb = f.getbbox(txt)
        im = Image.new("RGBA", (max(1, bb[2] - bb[0] + 8), max(1, bb[3] - bb[1] + 8)), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((4 - bb[0], 4 - bb[1]), txt, font=f, fill=col)
        _c[k] = im
    return _c[k]
def rrect(w, h, r, fill, contour=None, ep=0):
    w, h, r = max(1, int(w)), max(1, int(h)), int(r)
    k = ("rr", w, h, r, fill, contour, ep)
    if k not in _c:
        im = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
        ImageDraw.Draw(im).rounded_rectangle([0, 0, w * 2 - 1, h * 2 - 1], radius=r * 2, fill=fill, outline=contour, width=ep * 2)
        _c[k] = im.resize((w, h), Image.LANCZOS)
        if len(_c) > 600:
            _c.clear()
    return _c[k]
def ombre(w, h, r, flou=36, alpha=70, dy=26):
    k = ("om", w, h, r, flou, alpha, dy)
    if k not in _c:
        pad = flou * 3
        im = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
        ImageDraw.Draw(im).rounded_rectangle([pad, pad + dy, pad + w, pad + dy + h], radius=r, fill=(0, 0, 0, alpha))
        _c[k] = im.filter(ImageFilter.GaussianBlur(flou))
    return _c[k]
def poser(fond, im, cx, cy, ech=1.0, alpha=1.0, rot=0.0):
    if im is None or alpha <= 0.01 or ech <= 0.01:
        return
    if abs(ech - 1) > 0.004:
        im = im.resize((max(1, int(im.width * ech)), max(1, int(im.height * ech))), Image.BICUBIC)
    if abs(rot) > 0.15:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 0.99:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    fond.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))
def entre(fond, im, cx, cy, t, t0, d=0.7, mont=46, ech0=0.97):
    """Entrée « keynote » : monte de quelques pixels en fondu, avec un très léger zoom."""
    if t < t0:
        return
    p = out_expo(prog(t, t0, d))
    poser(fond, im, cx, cy + (1 - p) * mont, ech0 + (1 - ech0) * p, p)
def mot(fond, txt, taille, cx, cy, t, t0, col=INK, poids=900, d=0.7):
    entre(fond, texte(txt, taille, col, poids), cx, cy, t, t0, d)

# ---------- iPhone dessiné (générique, sans logo) ----------
def telephone(larg=330):
    k = ("tel", larg)
    if k in _c:
        return _c[k]
    s = 2
    w, h = larg * s, int(larg * 2.06) * s
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=int(w * .17), fill=(205, 205, 210))
    d.rounded_rectangle([5, 5, w - 6, h - 6], radius=int(w * .165), fill=(18, 18, 20))
    ins = int(w * .045)
    g = np.linspace(0, 1, h - 2 * ins)[:, None, None]
    arr = (np.array([255, 92, 88]) * (1 - g) + np.array([120, 12, 20]) * g).astype(np.uint8)
    arr = np.repeat(arr, w - 2 * ins, axis=1)
    ecran = Image.fromarray(np.dstack([arr, np.full(arr.shape[:2], 255, np.uint8)]), "RGBA")
    rond = Image.new("RGBA", ecran.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(rond)
    dr.ellipse([-ecran.width * .3, ecran.height * .5, ecran.width * .9, ecran.height * 1.1], fill=(255, 150, 140, 70))
    dr.ellipse([ecran.width * .3, ecran.height * .05, ecran.width * 1.3, ecran.height * .55], fill=(255, 255, 255, 38))
    ecran.alpha_composite(rond.filter(ImageFilter.GaussianBlur(50)))
    mq = Image.new("L", ecran.size, 0)
    ImageDraw.Draw(mq).rounded_rectangle([0, 0, ecran.width - 1, ecran.height - 1], radius=int(w * .15), fill=255)
    im.paste(ecran, (ins, ins), mq)
    d.rounded_rectangle([w * .36, ins + w * .04, w * .64, ins + w * .115], radius=int(w * .04), fill=(0, 0, 0))
    d.text((w / 2 - 60, h * 0.44), "", fill=BLANC)
    im = im.resize((w // s, h // s), Image.LANCZOS)
    _c[k] = im
    return im

def coche(taille, p, col=ROUGE):
    s = 3
    im = Image.new("RGBA", (taille * s, taille * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, taille * s - 1, taille * s - 1], fill=col)
    pts = [(0.28, 0.52), (0.44, 0.68), (0.74, 0.36)]
    pts = [(x * taille * s, y * taille * s) for x, y in pts]
    l1, l2 = math.dist(pts[0], pts[1]), math.dist(pts[1], pts[2])
    r = p * (l1 + l2)
    seg = [pts[0]]
    if r <= l1:
        u = r / l1; seg.append((pts[0][0] + (pts[1][0] - pts[0][0]) * u, pts[0][1] + (pts[1][1] - pts[0][1]) * u))
    else:
        u = (r - l1) / l2; seg += [pts[1], (pts[1][0] + (pts[2][0] - pts[1][0]) * u, pts[1][1] + (pts[2][1] - pts[1][1]) * u)]
    if p > 0:
        d.line(seg, fill=BLANC, width=int(taille * s * .1), joint="curve")
    return im.resize((taille, taille), Image.LANCZOS)

def icone(nom, taille=104):
    k = ("ic", nom, taille)
    if k in _c:
        return _c[k]
    s = 3
    T = taille * s
    im = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, T - 1, T - 1], fill=(235, 235, 240))
    u = T / 100
    if nom == "18":
        t = texte("18+", 40 * s, INK, 900, int(80 * u))
        im.alpha_composite(t, (int((T - t.width) / 2), int((T - t.height) / 2)))
    else:  # PC + iPhone
        d.rounded_rectangle([14 * u, 26 * u, 62 * u, 58 * u], radius=4 * u, outline=INK, width=int(5 * u))
        d.rectangle([34 * u, 58 * u, 42 * u, 68 * u], fill=INK)
        d.rounded_rectangle([26 * u, 68 * u, 50 * u, 73 * u], radius=2 * u, fill=INK)
        d.rounded_rectangle([60 * u, 40 * u, 82 * u, 74 * u], radius=5 * u, fill=ROUGE)
    im = im.resize((taille, taille), Image.LANCZOS)
    _c[k] = im
    return im

def carte(fond, t, t0, t_ok, cy, ic, titre, sous):
    """Carte blanche façon réglages : glisse en fondu, puis se coche en rouge."""
    if t < t0:
        return
    p = out_expo(prog(t, t0, 0.75))
    w, h = 800, 190
    c = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    c.alpha_composite(rrect(w, h, 48, BLANC + (255,)))
    c.alpha_composite(icone(ic), (40, (h - 104) // 2))
    c.alpha_composite(texte(titre, 54, INK, 800, 470), (178, 38))
    c.alpha_composite(texte(sous, 32, GRIS, 600, 470), (180, 108))
    if t_ok is not None and t >= t_ok:
        c.alpha_composite(coche(92, out_cubic(prog(t, t_ok, 0.4))), (w - 138, (h - 92) // 2))
    else:
        ImageDraw.Draw(c).ellipse([w - 138, (h - 92) // 2, w - 46, (h + 92) // 2], outline=(210, 210, 215), width=5)
    poser(fond, ombre(w, h, 48), CX, cy + (1 - p) * 70, 0.96 + 0.04 * p, p)
    sc = 1.0 + (0.035 * math.exp(-(t - t_ok) * 9) * math.cos((t - t_ok) * 26) if t_ok is not None and t >= t_ok else 0)
    poser(fond, c, CX, cy + (1 - p) * 70, (0.96 + 0.04 * p) * sc, p)

def pilule(txt, taille, fond_col, txt_col, px=56, py=24, poids=900):
    t_im = texte(txt, taille, txt_col, poids, 800 - 2 * px)
    w, h = t_im.width + 2 * px, t_im.height + 2 * py
    im = rrect(w, h, h // 2, fond_col).copy()
    im.alpha_composite(t_im, (px, py))
    return im

# ---------- scènes ----------
def coupe(m, n=1):
    return at(m, n) - 0.15
C2, C3, C4, C5, T_CTA = coupe("un"), coupe("deux"), coupe("être"), coupe("c'est"), coupe("commente")
T_OFFERT, T_OK1, T_OK2 = at("offert") - 0.05, at("majeur") + 0.3, at("iphone", 2) + 0.35
T_GO, T_ACC = at("go") - 0.05, at("t'accompagne")

def s1(f, t):
    mot(f, "La tech Apple", 84, CX, 640, t, 0.0, GRIS, 800)
    e = ressort(t, at("2k25") - 0.1, 2.2, 7)
    if t >= at("2k25") - 0.1:
        im = texte("2K25", 330, ROUGE, 900)
        poser(f, im, CX, 840, 0.92 + 0.08 * e, clamp((t - at("2k25") + 0.1) * 5))

def s2(f, t):
    # le téléphone flotte, légère rotation
    p = out_expo(prog(t, C2 + 0.05, 1.0))
    fl = math.sin(t * 1.8) * 9
    tel = telephone(228)
    poser(f, ombre(228, int(228 * 2.06), 70, 46, 55, 44), CX, 830 + fl * 0.4 + 26, 0.9 + 0.1 * p, p)
    poser(f, tel, CX, 830 + fl, 0.88 + 0.12 * p, p, (1 - p) * -6 + math.sin(t * 1.2) * 1.6)
    mot(f, "Un iPhone", 92, CX, 395, t, at("iphone") - 0.1, INK, 900)
    mot(f, "18 Pro.", 92, CX, 500, t, at("18") - 0.1, GRIS, 900)
    if t >= T_OFFERT:
        pl = pilule("Offert.", 84, ROUGE, BLANC)
        sc = 0.8 + 0.2 * ressort(t, T_OFFERT, 2.8, 8)
        poser(f, ombre(pl.width, pl.height, pl.height // 2, 30, 60, 20), CX, 1128, sc, clamp((t - T_OFFERT) * 7))
        poser(f, pl, CX, 1128, sc, clamp((t - T_OFFERT) * 7))

def s3(f, t):
    mot(f, "Deux", 190, CX, 700, t, C3 + 0.04, INK, 900, 0.8)
    mot(f, "conditions.", 150, CX, 900, t, at("conditions") - 0.08, GRIS, 900, 0.8)

def s4(f, t):
    mot(f, "Deux conditions", 62, CX, 400, t, C4 + 0.02, GRIS, 800, 0.6)
    carte(f, t, C4 + 0.05, T_OK1, 650, "18", "Être majeur", "18 ans minimum")
    carte(f, t, at("un", 2) - 0.1, T_OK2, 890, "pc", "Un PC ou un iPhone", "L'un ou l'autre suffit")

def s5(f, t):
    p = ressort(t, C5 + 0.02, 2.2, 7)
    poser(f, texte("C'est tout.", 200, INK, 900, 800), CX, 800, 0.9 + 0.1 * p, clamp((t - C5 - 0.02) * 6))

def s6(f, t):
    mot(f, "Commente", 170, CX, 640, t, T_CTA + 0.04, INK, 900, 0.8)
    if t >= T_GO:
        pl = pilule("GO", 190, ROUGE, BLANC, 100, 28)
        sc = 0.7 + 0.3 * ressort(t, T_GO, 2.6, 7) + (0.025 * math.sin((t - T_GO) * 6) if t > T_GO + 0.7 else 0)
        poser(f, ombre(pl.width, pl.height, pl.height // 2, 40, 80, 30), CX, 920, sc, clamp((t - T_GO) * 8))
        poser(f, pl, CX, 920, sc, clamp((t - T_GO) * 8))
    mot(f, "Je t'accompagne.", 72, CX, 1130, t, T_ACC - 0.05, GRIS, 800, 0.7)

SCENES = [(0.0, s1), (C2, s2), (C3, s3), (C4, s4), (C5, s5), (T_CTA, s6)]
PUNCH = [at("deux") - 0.1, T_OFFERT, T_OK1, T_OK2, C5 + 0.05, T_GO]
CHECKS = [T_OK1, T_OK2]
ENTREES = [C4 + 0.05, at("un", 2) - 0.1]
RAPPEL = C4

if "--timeline" in sys.argv:
    json.dump({"coupes": [d for d, _ in SCENES[1:]], "punchs": PUNCH, "coches": CHECKS, "entrees": ENTREES, "rappel": RAPPEL,
               "cta": T_CTA, "go": T_GO, "acc": T_ACC, "duree": DUREE}, open(sys.argv[sys.argv.index("--timeline") + 1], "w"), indent=1)
    sys.exit()

# ---------- sous-titres, tag ----------
ROUGES = {"2k25", "offert", "iphone", "pc", "majeur", "go", "tout"}
MORCEAUX, cur = [], []
for w in MOTS:
    cur.append(w)
    if len(cur) == 4 or w["t"][-1] in ".,?!:":
        MORCEAUX.append(cur); cur = []
if cur:
    MORCEAUX.append(cur)
def sous_titres(img, t):
    for j, m in enumerate(MORCEAUX):
        debut = m[0]["s"] - 0.1
        fin = MORCEAUX[j + 1][0]["s"] - 0.1 if j + 1 < len(MORCEAUX) else DUREE
        fin = min(fin, m[-1]["e"] + 0.6)
        if not (debut <= t < fin):
            continue
        tail = 54
        f = police(800, tail)
        sp = f.getlength(" ")
        lw = sum(f.getlength(w["t"]) for w in m) + sp * (len(m) - 1)
        while lw > 740:
            tail -= 2; f = police(800, tail); sp = f.getlength(" ")
            lw = sum(f.getlength(w["t"]) for w in m) + sp * (len(m) - 1)
        y = 1310
        img.alpha_composite(rrect(lw + 70, tail + 44, (tail + 44) // 2, (255, 255, 255, 215)), (int(CX - lw / 2 - 35), int(y - 16)))
        d = ImageDraw.Draw(img)
        x = CX - lw / 2
        for w in m:
            if t >= w["s"] - 0.1:
                actif = w["s"] - 0.1 <= t < w["e"] + 0.05
                cle = w["t"].lower().strip(".,?!:") in ROUGES
                d.text((x, y), w["t"], font=f, fill=ROUGE if (actif and cle) else (INK if t >= w["s"] - 0.1 else GRIS))
            x += f.getlength(w["t"]) + sp

def tag(img, t):
    """Nom d'utilisateur : saute d'une place à l'autre (anti-copie) ; signature en fin de vidéo."""
    pp = police(800, 34)
    if t < T_CTA:
        x, y = PLACES[int(t / PERIODE) % len(PLACES)]
        im = texte(HANDLE, 34, (110, 110, 118), 800)
        poser(img, im, x, y, 1, 0.8)
    if t >= T_ACC + 0.4:
        im = texte(f"{NOM} · {HANDLE}", 38, GRIS, 800)
        poser(img, im, CX, 1215, 1, clamp((t - T_ACC - 0.4) * 4))

# ---------- image ----------
TRANS = 0.38
def couche(fn, t):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fn(lay, t)
    return lay
def image(t):
    img = Image.new("RGBA", (W, H), BG + (255,))
    i = 0
    for k, (d, _) in enumerate(SCENES):
        if t >= d:
            i = k
    d0, fn = SCENES[i]
    if i > 0 and t - d0 < TRANS:
        p = in_out((t - d0) / TRANS)
        poser(img, couche(SCENES[i - 1][1], t), W / 2, H / 2, 1 - 0.05 * p, 1 - p)
        poser(img, couche(fn, t), W / 2, H / 2, 1.05 - 0.05 * p, p)
    else:
        img.alpha_composite(couche(fn, t))
    tag(img, t)
    sous_titres(img, t)
    if t < 0.12:  # fondu d'entrée très court
        img = Image.blend(Image.new("RGBA", (W, H), BG + (255,)), img, clamp(t / 0.12 + 0.35))
    return img.convert("RGB")

if STILLS:
    for s in STILLS:
        image(s).save(os.path.join(os.path.dirname(SORTIE), f"still-{s:05.2f}.png"))
    sys.exit()
AUDIO = os.path.join(os.path.dirname(SORTIE), "mix.wav")
cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", AUDIO,
       "-c:v", "libx264", "-preset", "medium", "-b:v", "12M", "-maxrate", "14M", "-bufsize", "24M", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", SORTIE]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for n in range(NF):
    p.stdin.write(image(n / FPS).tobytes())
p.stdin.close()
p.wait()
