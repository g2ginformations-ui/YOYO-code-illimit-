"""Tech Apple 2K25 — 4 vidéos format « pub » (fonds pleins noir / rouge, mots plein écran, coupes sèches).

Usage : python3 pub.py <voix.wav> <dossier_polices> <sortie.mp4> --video 1|2|3|4|5 [--stills t1,...] [--timeline f.json]
  1 « Sans »     : sans prise de tête, sans cravate, sans te ruiner (mots barrés).
  2 « Bravo »    : tu trouves toujours le bon plan... fais pareil pour ton iPhone (texte en relief, rayons).
  3 « 1·1·1 »    : 1 majeur, 1 PC ou 1 iPhone, 1 commentaire (liste qui s'empile).
  4 « Partout »  : dans ton lit, dans le bus, entre deux cours (pictos).
  5 « Les cases »: iPhone 18 Pro offert -> 2 cases cochées -> la 3e case, c'est ton commentaire.
Les instants des mots viennent de mots_<video>.json ; le son de out/mix.wav (synth_pub.py).
"""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ICI))
from tag_marque import tag_mobile, signature  # tag anti-copie (videos/marque.json)

VOIX, POLICES, SORTIE = sys.argv[1], sys.argv[2], sys.argv[3]
VIDEO = sys.argv[sys.argv.index("--video") + 1] if "--video" in sys.argv else "1"
STILLS = [float(x) for x in sys.argv[sys.argv.index("--stills") + 1].split(",")] if "--stills" in sys.argv else None

W, H, FPS = 1080, 1920, 30
CX = 520  # axe central de la zone sûre TikTok (x 120 à 920, y 280 à 1440)
NOIR, ROUGE, ROUGE_F, BLANC = (12, 11, 13), (232, 38, 43), (150, 16, 22), (246, 243, 238)
FIN_HOLD = 1.5

with wave.open(VOIX) as wf:
    FIN_VOIX = wf.getnframes() / wf.getframerate()
DUREE = FIN_VOIX + FIN_HOLD
NF = int(round(DUREE * FPS))

MOTS = [{"t": w["text"], "s": w["start"], "e": w["end"]}
        for w in json.load(open(os.path.join(ICI, f"mots_{VIDEO}.json")))["words"] if w["type"] == "word"]
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
def out_cubic(p):
    return 1 - (1 - p) ** 3
def ressort(t, t0, freq=3.0, amort=8.0):
    x = t - t0
    return 0.0 if x <= 0 else 1 - math.exp(-amort * x) * math.cos(2 * math.pi * freq * x)

# ---------- polices, textes ----------
_f = {}
def police(nom, taille):
    k = (nom, taille)
    if k not in _f:
        fichier = "anton-latin-400-normal.woff" if nom == "anton" else f"poppins-latin-{nom}-normal.woff"
        _f[k] = ImageFont.truetype(os.path.join(POLICES, fichier), taille)
    return _f[k]

_c = {}
def texte(txt, taille, col=BLANC, nom="anton", max_l=800):
    k = ("t", txt, taille, col, nom, max_l)
    if k not in _c:
        f = police(nom, taille)
        while f.getlength(txt) > max_l and taille > 20:
            taille -= 4
            f = police(nom, taille)
        bb = f.getbbox(txt)
        im = Image.new("RGBA", (bb[2] - bb[0] + 8, bb[3] - bb[1] + 8), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((4 - bb[0], 4 - bb[1]), txt, font=f, fill=col)
        _c[k] = im
    return _c[k]

def poser(fond, im, cx, cy, ech=1.0, alpha=1.0, rot=0.0):
    if im is None or alpha <= 0.01 or ech <= 0.01:
        return
    if abs(ech - 1) > 0.005:
        im = im.resize((max(1, int(im.width * ech)), max(1, int(im.height * ech))), Image.BICUBIC)
    if abs(rot) > 0.2:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 0.99:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    fond.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def tape(t, t0):
    """Échelle d'un mot qui « tape » : 1,3 -> 1 en 0,12 s avec un léger rebond."""
    if t < t0:
        return None
    return 1 + 0.3 * math.exp(-(t - t0) * 22) * math.cos((t - t0) * 30)

def mot(fond, txt, taille, cx, cy, t, t0, col=BLANC, rot=0.0, nom="anton"):
    """Mot plein écran qui tape à l'arrivée ; renvoie sa taille (pour barrer)."""
    e = tape(t, t0)
    im = texte(txt, taille, col, nom)
    if e is not None:
        poser(fond, im, cx, cy, e, 1, rot)
    return im.size

def barre(fond, cx, cy, l, h, t, t0, col):
    """Trait qui barre un mot : se dessine de gauche à droite en 0,15 s."""
    if t < t0:
        return
    p = out_cubic(prog(t, t0, 0.15))
    ep = max(14, int(h * 0.12))
    x0 = cx - l / 2 - 20
    ImageDraw.Draw(fond).rounded_rectangle([x0, cy - ep / 2 + 6, x0 + (l + 40) * p, cy + ep / 2 + 6],
                                           radius=ep // 2, fill=col)

def relief(txt, taille, face, cote, prof=22, penche=0.2):
    """Texte en relief penché (face + tranche), façon affiche."""
    k = ("r", txt, taille, face, cote, prof, penche)
    if k in _c:
        return _c[k]
    f = police("anton", taille)
    while f.getlength(txt) > 760 and taille > 40:
        taille -= 4
        f = police("anton", taille)
    bb = f.getbbox(txt)
    w, h = bb[2] - bb[0] + 20, bb[3] - bb[1] + 20
    m = Image.new("L", (w + int(h * penche) + 10, h), 0)
    ImageDraw.Draw(m).text((10 - bb[0] + int(h * penche), 10 - bb[1]), txt, font=f, fill=255)
    m = m.transform(m.size, Image.AFFINE, (1, penche, -h * penche * 0.5, 0, 1, 0), resample=Image.BICUBIC)
    im = Image.new("RGBA", (m.width + prof + 8, m.height + prof + 8), (0, 0, 0, 0))
    contour = m.filter(ImageFilter.MaxFilter(9))
    for i in range(prof, 0, -1):
        im.paste(Image.new("RGBA", m.size, cote + (255,)), (i + 4, i + 4), contour)
    im.paste(Image.new("RGBA", m.size, (12, 11, 13, 255)), (4, 4), contour)
    im.paste(Image.new("RGBA", m.size, face + (255,)), (4, 4), m)
    _c[k] = im
    return im

def rayons(fond, cx, cy, t, col, n=18, alpha=70):
    """Soleil de rayons qui tourne lentement derrière un mot."""
    d = ImageDraw.Draw(fond)
    a0 = t * 0.25
    for j in range(n):
        a = a0 + j * 2 * math.pi / n
        b = a + math.pi / n
        d.polygon([(cx, cy), (cx + math.cos(a) * 1600, cy + math.sin(a) * 1600),
                   (cx + math.cos(b) * 1600, cy + math.sin(b) * 1600)], fill=col + (alpha,))

def etoile(r):
    k = ("e", r)
    if k not in _c:
        s = 3
        im = Image.new("RGBA", (r * 2 * s, r * 2 * s), (0, 0, 0, 0))
        c = r * s
        pts = []
        for j in range(8):
            a = j * math.pi / 4
            rr = c if j % 2 == 0 else c * 0.22
            pts.append((c + math.cos(a) * rr, c + math.sin(a) * rr))
        ImageDraw.Draw(im).polygon(pts, fill=BLANC)
        _c[k] = im.resize((r * 2, r * 2), Image.LANCZOS)
    return _c[k]

ETOILES = [(170, 420), (880, 380), (210, 1080), (860, 1010), (520, 300), (150, 760), (900, 700)]
def etoiles(fond, t, t0, n=5):
    if t < t0:
        return
    for j, (x, y) in enumerate(ETOILES[:n]):
        s = 0.5 + 0.5 * abs(math.sin((t - t0) * 3 + j * 1.7))
        poser(fond, etoile(26), x, y, s * min(1, (t - t0) * 6))

# ---------- objets dessinés ----------
def rrect(w, h, r, fill, contour=None, ep=0):
    w, h, r = int(w), int(h), int(r)
    k = ("rr", w, h, r, fill, contour, ep)
    if k not in _c:
        im = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
        ImageDraw.Draw(im).rounded_rectangle([0, 0, w * 2 - 1, h * 2 - 1], radius=r * 2, fill=fill,
                                             outline=contour, width=ep * 2)
        _c[k] = im.resize((w, h), Image.LANCZOS)
    return _c[k]

def pilule(txt, taille, fond_col, txt_col, px=44, py=20, nom="anton"):
    t_im = texte(txt, taille, txt_col, nom, 760 - 2 * px)
    w, h = t_im.width + 2 * px, t_im.height + 2 * py
    im = rrect(w, h, h // 2, fond_col).copy()
    im.alpha_composite(t_im, (px, py))
    return im

def telephone(larg=300):
    k = ("tel", larg)
    if k in _c:
        return _c[k]
    s = 2
    w, h = larg * s, int(larg * 2.06) * s
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=int(w * 0.19), fill=(40, 38, 42))
    d.rounded_rectangle([6, 6, w - 7, h - 7], radius=int(w * 0.18), fill=(14, 13, 15))
    ins = int(w * 0.045)
    g = np.linspace(0, 1, h - 2 * ins)[:, None]
    top, bas = np.array([255, 70, 70]), np.array([60, 8, 12])
    arr = (top * (1 - g) + bas * g).astype(np.uint8)
    arr = np.repeat(arr[:, None, :], w - 2 * ins, axis=1)
    ecran = Image.fromarray(np.dstack([arr, np.full(arr.shape[:2], 255, np.uint8)]), "RGBA")
    masque = Image.new("L", ecran.size, 0)
    ImageDraw.Draw(masque).rounded_rectangle([0, 0, ecran.width - 1, ecran.height - 1], radius=int(w * 0.15), fill=255)
    im.paste(ecran, (ins, ins), masque)
    d.rounded_rectangle([w * 0.36, ins + w * 0.04, w * 0.64, ins + w * 0.115], radius=int(w * 0.04), fill=(0, 0, 0))
    im = im.resize((w // s, h // s), Image.LANCZOS)
    _c[k] = im
    return im

def picto(nom, taille=320, col=BLANC):
    """Pictos plats : lit, bus, livres (les trous sont transparents)."""
    k = ("p", nom, taille, col)
    if k in _c:
        return _c[k]
    s = 3
    T = taille * s
    im = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    vide = (0, 0, 0, 0)
    u = T / 100
    if nom == "lit":
        d.rounded_rectangle([8 * u, 30 * u, 18 * u, 82 * u], radius=3 * u, fill=col)        # tête de lit
        d.rounded_rectangle([8 * u, 55 * u, 92 * u, 72 * u], radius=4 * u, fill=col)        # matelas
        d.rounded_rectangle([22 * u, 44 * u, 40 * u, 54 * u], radius=4 * u, fill=col)       # oreiller
        d.rounded_rectangle([42 * u, 46 * u, 92 * u, 56 * u], radius=4 * u, fill=col)       # couette
        d.rectangle([84 * u, 72 * u, 92 * u, 82 * u], fill=col)
    elif nom == "bus":
        d.rounded_rectangle([10 * u, 22 * u, 90 * u, 76 * u], radius=10 * u, fill=col)
        for x in (18, 40, 62):
            d.rounded_rectangle([x * u, 30 * u, (x + 18) * u, 48 * u], radius=3 * u, fill=vide)
        d.rectangle([10 * u, 58 * u, 90 * u, 60 * u], fill=vide)
        for x in (28, 72):
            d.ellipse([(x - 9) * u, 68 * u, (x + 9) * u, 86 * u], fill=col)
            d.ellipse([(x - 4) * u, 73 * u, (x + 4) * u, 81 * u], fill=vide)
    else:  # livres
        for j, (x0, y0, x1, y1) in enumerate([(14, 66, 86, 82), (20, 48, 80, 64), (10, 30, 74, 46)]):
            d.rounded_rectangle([x0 * u, y0 * u, x1 * u, y1 * u], radius=3 * u, fill=col)
            d.rectangle([(x0 + 6) * u, (y0 + 4) * u, (x0 + 9) * u, (y1 - 4) * u], fill=vide)
    im = im.resize((taille, taille), Image.LANCZOS)
    _c[k] = im
    return im

def curseur():
    k = ("cur",)
    if k not in _c:
        s = 3
        im = Image.new("RGBA", (60 * s, 80 * s), (0, 0, 0, 0))
        pts = [(0, 0), (0, 64), (16, 50), (27, 75), (38, 70), (27, 46), (48, 46)]
        pts = [(x * s + 4, y * s + 4) for x, y in pts]
        d = ImageDraw.Draw(im)
        d.polygon(pts, fill=NOIR)
        d.line(pts + [pts[0]], fill=BLANC, width=4 * s, joint="curve")
        _c[k] = im.resize((60, 80), Image.LANCZOS)
    return _c[k]

# ---------- briques de scène ----------
def fond_plein(img, col):
    img.paste(col + (255,), (0, 0, W, H))

def sc_iphone(img, t, t0, t_gratuit, titre=("IPHONE 18 PRO",), fond=NOIR, pastille="GRATUIT"):
    """Le téléphone qui tape au centre + pilule GRATUIT."""
    fond_plein(img, fond)
    rayons(img, CX, 760, t, ROUGE if fond == NOIR else NOIR, 18, 40)
    deux = len(titre) > 1
    for j, l in enumerate(titre):
        mot(img, l, 110 if deux else 120, CX, (390 if deux else 400) + j * 115, t, t0 - 0.05 + j * 0.1)
    e = tape(t, t0 + 0.05)
    if e:
        poser(img, telephone(230 if deux else 270), CX, 845 if deux else 800, e, 1, math.sin(t * 2) * 3)
    if t >= t_gratuit:
        e = tape(t, t_gratuit)
        poser(img, pilule(pastille, 110, ROUGE if fond == NOIR else BLANC, BLANC if fond == NOIR else ROUGE), CX, 1060, e, 1, -6)
        etoiles(img, t, t_gratuit, 6)

def sc_pile(img, t, lignes, fond=ROUGE, y0=430, pas=150, taille=130):
    """Liste qui s'empile : chaque ligne (texte, instant, couleur) tape à son mot."""
    fond_plein(img, fond)
    for j, (txt, t0, col) in enumerate(lignes):
        mot(img, txt, taille, CX, y0 + j * pas, t, t0, col)

def sc_fin(img, t, t0, t_go, t_acc, bas="GRATUITEMENT", t_bas=None):
    """Fin façon pub : COMMENTE + champ « GO » cliqué par un curseur + je t'accompagne gratuitement."""
    fond_plein(img, NOIR)
    etoiles(img, t, t0, 4)
    mot(img, "COMMENTE", 190, CX, 470, t, t0)
    # champ de commentaire : contour rouge, « GO » s'écrit, puis le curseur clique et le champ se remplit
    clic = t_go + 0.35
    plein = t >= clic
    champ = rrect(560, 170, 85, (ROUGE if plein else NOIR) + (255,), ROUGE + (255,), 8).copy()
    n = 0 if t < t_go - 0.05 else min(2, int((t - t_go + 0.05) / 0.1) + 1)
    if n:
        g = texte("GO"[:n], 130, BLANC)
        champ.alpha_composite(g, (280 - texte("GO", 130, BLANC).width // 2, 85 - g.height // 2))
    e = 1.0 if not plein else 1 + 0.12 * math.exp(-(t - clic) * 14) * math.cos((t - clic) * 30)
    poser(img, champ, CX, 720, e)
    if t >= clic and t < clic + 0.5:  # onde du clic
        p = (t - clic) / 0.5
        r = 100 + 260 * p
        ImageDraw.Draw(img).ellipse([CX - r, 720 - r * 0.5, CX + r, 720 + r * 0.5], outline=ROUGE + (int(255 * (1 - p)),), width=6)
    # curseur : arrive d'en bas à droite, clique, puis s'écarte un peu
    if t >= t0 + 0.2:
        p = out_cubic(prog(t, t0 + 0.2, max(0.2, clic - t0 - 0.3)))
        x = 900 + (CX + 140 - 900) * p
        y = 1150 + (750 - 1150) * p
        e = 0.85 if clic <= t < clic + 0.12 else 1
        poser(img, curseur(), x + 30, y + 40, e)
    if t >= t_acc - 0.08:
        mot(img, "JE T'ACCOMPAGNE", 110, CX, 930, t, t_acc - 0.08)
        mot(img, bas, 120, CX, 1050, t, t_bas if t_bas is not None else t_acc + 0.12, ROUGE)

def coupe(mot_, n=1):
    return at(mot_, n) - 0.15

# ---------- les 4 vidéos ----------
if VIDEO == "1":  # « Sans »
    C2, C3, C4, C5, C6, C7 = coupe("sans", 2), coupe("sans", 3), coupe("avec"), coupe("l'iphone"), coupe("un"), coupe("parce")
    def sans(img, t, t0, txt, fond, col_barre, t_barre):
        fond_plein(img, fond)
        mot(img, "SANS", 120, CX, 560, t, t0)
        l, h = mot(img, txt, 190, CX, 760, t, t0 + 0.1)
        if t >= t0 + 0.1:
            barre(img, CX, 760, l, h, t, t_barre, col_barre)
    def b4(img, t):
        fond_plein(img, ROUGE)
        rayons(img, CX, 760, t, NOIR, 18, 30)
        mot(img, "AVEC LA", 110, CX, 500, t, C4 + 0.03)
        mot(img, "TECH APPLE", 170, CX, 660, t, at("tech") - 0.05)
        e = tape(t, at("2k25") - 0.05)
        if e:
            poser(img, relief("2K25", 260, BLANC, NOIR), CX, 950, e, 1, -5)
        etoiles(img, t, at("2k25"), 6)
    def b6(img, t):
        sc_pile(img, t, [("1. MAJEUR", at("un") - 0.05, BLANC), ("2. UN PC", at("deux") - 0.05, BLANC),
                         ("OU UN IPHONE", at("iphone") - 0.1, NOIR)], ROUGE, 520, 190, 160)
    def b7(img, t):
        fond_plein(img, NOIR)
        mot(img, "LE DERNIER IPHONE", 130, CX, 500, t, C7 + 0.03)
        mot(img, "ÇA DOIT PAS", 160, CX, 700, t, at("ça") - 0.05, ROUGE)
        mot(img, "COÛTER CHER", 160, CX, 880, t, at("coûter") - 0.05, ROUGE)
    BEATS = [
        (0, lambda img, t: sans(img, t, -0.15, "PRISE DE TÊTE", NOIR, ROUGE, at("tête") + 0.12)),
        (C2, lambda img, t: sans(img, t, C2, "CRAVATE", ROUGE, NOIR, at("cravate") + 0.2)),
        (C3, lambda img, t: sans(img, t, C3, "TE RUINER", NOIR, ROUGE, at("ruiner") + 0.2)),
        (C4, b4),
        (C5, lambda img, t: sc_iphone(img, t, C5 + 0.05, at("gratuit") - 0.05)),
        (C6, b6),
        (C7, b7),
    ]
    PUNCH = [at("tête") + 0.12, at("cravate") + 0.2, at("ruiner") + 0.2, at("2k25") - 0.05, at("gratuit") - 0.05]
    CHECKS = [at("un") - 0.05, at("deux") - 0.05]
    RAPPEL = C6
elif VIDEO == "2":  # « Bravo »
    C2, C3, C4, C5, C6, C7, C8 = (coupe("tu"), coupe("le", 2), coupe("le", 3), coupe("fais"), coupe("la"),
                                  coupe("l'iphone"), coupe("t'es"))
    def affiche(img, t, t0, txt, fond, face, cote, ray, petit=None, rot=-6):
        fond_plein(img, fond)
        rayons(img, CX, 760, t, ray, 18, 60)
        if petit:
            mot(img, petit, 80, CX, 470, t, C2 + 0.03, BLANC, 0, "800")
        e = tape(t, t0)
        if e:
            poser(img, relief(txt, 230, face, cote), CX, 780, e, 1, rot)
        etoiles(img, t, t0, 5)
    def b5(img, t):
        fond_plein(img, NOIR)
        for j, (l, col) in enumerate([("FAIS PAREIL", BLANC), ("POUR TON", BLANC), ("IPHONE", ROUGE)]):
            e = tape(t, C5 + 0.03 + j * 0.18)
            if e:
                poser(img, relief(l, 170, col, ROUGE_F if col == BLANC else (90, 8, 12), 14, 0.15), CX, 560 + j * 200, e, 1, 8)
    def b6(img, t):
        fond_plein(img, ROUGE)
        # téléphones qui jaillissent en éventail
        p = out_cubic(prog(t, C6 + 0.05, 0.6))
        for j in range(8):
            a = j * math.pi / 4 + 0.3
            poser(img, telephone(150), CX + math.cos(a) * 330 * p, 760 + math.sin(a) * 420 * p, 0.6 + 0.4 * p,
                  min(1, p * 3), math.degrees(a) * 0.4 * p)
        mot(img, "TECH APPLE", 170, CX, 680, t, at("tech") - 0.05)
        mot(img, "2K25", 280, CX, 900, t, at("2k25") - 0.05, NOIR)
    def b8(img, t):
        sc_pile(img, t, [("MAJEUR ?", at("majeur") - 0.05, BLANC), ("UN PC OU", at("pc") - 0.08, BLANC),
                         ("UN IPHONE ?", at("iphone", 2) - 0.08, BLANC), ("C'EST TOUT.", at("c'est") - 0.05, NOIR)],
                 ROUGE, 440, 175, 150)
    BEATS = [
        (0, lambda img, t: affiche(img, t, -0.15, "BRAVO", ROUGE, BLANC, NOIR, ROUGE_F)),
        (C2, lambda img, t: affiche(img, t, at("bon") - 0.08, "LE BON PLAN", ROUGE, BLANC, NOIR, ROUGE_F, "TU TROUVES TOUJOURS")),
        (C3, lambda img, t: affiche(img, t, at("cool") - 0.1, "COOL", NOIR, ROUGE, BLANC, ROUGE_F, None, 0)),
        (C4, lambda img, t: affiche(img, t, at("chemin") - 0.05, "LE PLUS COURT", ROUGE, BLANC, NOIR, ROUGE_F, None, 8)),
        (C5, b5),
        (C6, b6),
        (C7, lambda img, t: sc_iphone(img, t, C7 + 0.05, at("gratuit") - 0.05)),
        (C8, b8),
    ]
    PUNCH = [0.0, at("bon") - 0.08, at("cool") - 0.1, at("chemin") - 0.05, at("2k25") - 0.05, at("gratuit") - 0.05,
             at("c'est") - 0.05]
    CHECKS = [at("majeur") - 0.05, at("iphone", 2) - 0.08]
    RAPPEL = C7
elif VIDEO == "3":  # « 1·1·1 »
    C2, C3 = coupe("pour"), coupe("la")
    def b1(img, t):
        sc_pile(img, t, [("1 MAJEUR", -0.15, BLANC), ("1 PC OU 1 IPHONE", at("un", 2) - 0.05, BLANC),
                         ("1 COMMENTAIRE", at("un", 4) - 0.05, NOIR)], ROUGE, 560, 190, 165)
    def b3(img, t):
        fond_plein(img, NOIR)
        mot(img, "LA TECH APPLE", 150, CX, 520, t, C3 + 0.03)
        mot(img, "2K25", 300, CX, 760, t, at("2k25") - 0.05, ROUGE)
        mot(img, "TOUT SIMPLEMENT.", 130, CX, 1000, t, at("tout") - 0.05)
    BEATS = [
        (0, b1),
        (C2, lambda img, t: sc_iphone(img, t, C2 + 0.05, at("gratuit") - 0.05, ("POUR 1", "IPHONE 18 PRO"), ROUGE)),
        (C3, b3),
    ]
    PUNCH = [at("un", 2) - 0.05, at("un", 4) - 0.05, at("gratuit") - 0.05, at("2k25") - 0.05, at("tout") - 0.05]
    CHECKS = [at("un", 2) - 0.05, at("un", 4) - 0.05]
    RAPPEL = C2
elif VIDEO == "5":  # « Les cases » : la synthèse (résultat d'abord, cases à cocher, le commentaire = 3e case)
    C2, C3 = coupe("grâce"), coupe("tu")
    def ligne_case(img, t, y, label, t_app, t_ok, col=BLANC, attente=False):
        """Case carrée + libellé ; se coche en rouge à t_ok ; en attente : contour qui clignote et « ? »."""
        e = tape(t, t_app)
        if e is None:
            return
        c = 120
        box = Image.new("RGBA", (c * 3, c * 3), (0, 0, 0, 0))
        d = ImageDraw.Draw(box)
        clign = attente and math.floor(t * 4) % 2 == 0
        d.rounded_rectangle([12, 12, c * 3 - 12, c * 3 - 12], radius=30, outline=ROUGE if clign else BLANC, width=30)
        if t_ok is not None and t >= t_ok:
            p = out_cubic(prog(t, t_ok, 0.25))
            pts = [(0.22, 0.52), (0.42, 0.72), (0.8, 0.28)]
            pts = [(x * c * 3, y_ * c * 3) for x, y_ in pts]
            l1, l2 = math.dist(pts[0], pts[1]), math.dist(pts[1], pts[2])
            r = p * (l1 + l2)
            seg = [pts[0]]
            if r <= l1:
                u = r / l1; seg.append((pts[0][0] + (pts[1][0] - pts[0][0]) * u, pts[0][1] + (pts[1][1] - pts[0][1]) * u))
            else:
                u = (r - l1) / l2; seg += [pts[1], (pts[1][0] + (pts[2][0] - pts[1][0]) * u, pts[1][1] + (pts[2][1] - pts[1][1]) * u)]
            d.line(seg, fill=ROUGE, width=44, joint="curve")
        box = box.resize((c, c), Image.LANCZOS)
        if attente:
            q = texte("?", 90, ROUGE)
            box.alpha_composite(q, (c // 2 - q.width // 2, c // 2 - q.height // 2))
        poser(img, box, 210, y, e)
        lab = texte(label, 96, col, "anton", 600)
        poser(img, lab, 290 + lab.width / 2, y, e)
    def b3(img, t):
        fond_plein(img, NOIR)
        mot(img, "TU COCHES", 120, CX, 400, t, C3 + 0.03)
        mot(img, "2 CASES", 150, CX, 540, t, at("deux") - 0.05, ROUGE)
        ligne_case(img, t, 720, "MAJEUR", at("t'es") - 0.08, at("majeur") + 0.2)
        ligne_case(img, t, 880, "PC OU IPHONE", at("t'as") - 0.08, at("iphone") + 0.2)
        ligne_case(img, t, 1040, "TON COMMENTAIRE", at("troisième") - 0.05, None, ROUGE, True)
    BEATS = [
        (0, lambda img, t: sc_iphone(img, t, -0.15, at("offert") - 0.05, pastille="OFFERT")),
        (C2, lambda img, t: (fond_plein(img, ROUGE), rayons(img, CX, 760, t, NOIR, 18, 30),
                             mot(img, "GRÂCE À LA", 110, CX, 500, t, C2 + 0.03),
                             mot(img, "TECH APPLE", 170, CX, 660, t, at("tech") - 0.05),
                             poser(img, relief("2K25", 260, BLANC, NOIR), CX, 950, tape(t, at("2k25") - 0.05) or 0, 1, -5),
                             etoiles(img, t, at("2k25"), 6))),
        (C3, b3),
    ]
    PUNCH = [at("offert") - 0.05, at("2k25") - 0.05, at("majeur") + 0.2, at("iphone") + 0.2, at("troisième") - 0.05]
    CHECKS = [at("majeur") + 0.2, at("iphone") + 0.2]
    RAPPEL = C3
else:  # « Partout »
    C2, C3, C4, C5, C6 = coupe("dans", 2), coupe("entre"), coupe("la"), coupe("il"), coupe("l'iphone")
    def lieu(img, t, t0, nom, l1, l2, fond):
        fond_plein(img, fond)
        e = tape(t, t0)
        if e:
            poser(img, picto(nom, 380), CX, 620, e)
        mot(img, l1, 120, CX, 900, t, t0 + 0.08)
        mot(img, l2, 170, CX, 1060, t, t0 + 0.16, NOIR if fond == ROUGE else ROUGE)
    def b4(img, t):
        fond_plein(img, NOIR)
        mot(img, "TECH APPLE", 170, CX, 480, t, C4 + 0.03)
        mot(img, "2K25", 260, CX, 690, t, at("2k25") - 0.05, ROUGE)
        e = tape(t, at("partout") - 0.05)
        if e:
            for j, nom in enumerate(("lit", "bus", "livres")):  # les pictos tournent derrière le mot
                a = t * 1.2 + j * 2 * math.pi / 3
                poser(img, picto(nom, 110), CX + math.cos(a) * 400, 1000 + math.sin(a) * 170, 1, 0.55)
            poser(img, relief("PARTOUT", 210, BLANC, ROUGE), CX, 1000, e, 1, -6)
    def b5(img, t):
        sc_pile(img, t, [("IL TE FAUT JUSTE", C5 + 0.03, BLANC), ("ÊTRE MAJEUR", at("majeur") - 0.08, NOIR),
                         ("UN PC OU", at("pc") - 0.08, BLANC), ("UN IPHONE", at("iphone") - 0.08, BLANC)],
                 ROUGE, 440, 175, 140)
    BEATS = [
        (0, lambda img, t: lieu(img, t, -0.15, "lit", "DANS", "TON LIT", ROUGE)),
        (C2, lambda img, t: lieu(img, t, C2, "bus", "DANS", "LE BUS", NOIR)),
        (C3, lambda img, t: lieu(img, t, C3, "livres", "ENTRE", "DEUX COURS", ROUGE)),
        (C4, b4),
        (C5, b5),
        (C6, lambda img, t: sc_iphone(img, t, C6 + 0.05, at("gratuit") - 0.05)),
    ]
    PUNCH = [C2, C3, at("2k25") - 0.05, at("partout") - 0.05, at("gratuit") - 0.05]
    CHECKS = [at("majeur") - 0.08, at("iphone") - 0.08]
    RAPPEL = C5

T_CTA = coupe("commente")
T_GO = at("go") - 0.05
T_ACC = at("t'accompagne")
if VIDEO == "5":
    BEATS.append((T_CTA, lambda img, t: sc_fin(img, t, T_CTA, T_GO, T_ACC, "C'EST OFFERT", at("c'est", 2) - 0.05)))
else:
    BEATS.append((T_CTA, lambda img, t: sc_fin(img, t, T_CTA, T_GO, T_ACC)))
PUNCH.append(T_GO + 0.35)

if "--timeline" in sys.argv:  # instants clés pour synth_pub.py
    json.dump({"coupes": [d for d, _ in BEATS[1:]], "punchs": PUNCH, "coches": CHECKS, "entrees": [],
               "rappel": RAPPEL, "cta": T_CTA, "go": T_GO, "acc": T_ACC, "duree": DUREE},
              open(sys.argv[sys.argv.index("--timeline") + 1], "w"), indent=1)
    sys.exit()

def rappel(img, t):
    if RAPPEL <= t < T_CTA:
        poser(img, pilule("COMMENTE GO", 44, BLANC, NOIR, 30, 12), CX, 1175, tape(t, RAPPEL) or 1)

def image(t):
    img = Image.new("RGBA", (W, H), NOIR + (255,))
    fn = BEATS[0][1]
    for d, f in BEATS:
        if t >= d:
            fn = f
    fn(img, t)
    rappel(img, t)
    pp = os.path.join(POLICES, "poppins-latin-800-normal.woff")
    tag_mobile(img, t, pp, T_CTA)
    signature(img, t, pp, T_ACC + 0.3)
    # secousse sur les coups forts
    for pt in PUNCH:
        x = t - pt
        if 0 <= x < 0.2:
            amp = 16 * (1 - x / 0.2)
            sh = Image.new("RGBA", (W, H), NOIR + (255,))
            sh.paste(img, (int(math.sin(x * 120) * amp), int(math.cos(x * 90) * amp * 0.5)))
            img = sh
            break
    return img.convert("RGB")

if STILLS:
    for s in STILLS:
        image(s).save(os.path.join(os.path.dirname(SORTIE), f"still-{s:05.2f}.png"))
    sys.exit()

AUDIO = os.path.join(os.path.dirname(SORTIE), "mix.wav")
cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
       "-i", "-", "-i", AUDIO, "-c:v", "libx264", "-preset", "medium", "-b:v", "10M", "-maxrate", "12M",
       "-bufsize", "20M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", SORTIE]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for n in range(NF):
    p.stdin.write(image(n / FPS).tobytes())
p.stdin.close()
p.wait()
