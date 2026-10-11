"""Tech Apple 2k25, la version « chaque jour » — DA pixel noir et rouge, 1080x1920, 30 i/s, calée sur la voix ElevenLabs (texte.txt).

Usage : python3 rendu.py <voix.wav> <dossier_polices> <sortie.mp4> [--stills t1,t2,...]
Les instants des mots viennent de mots.json (transcription mot à mot de la voix).
"""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ICI = os.path.dirname(os.path.abspath(__file__))
VOIX, POLICES, SORTIE = sys.argv[1], sys.argv[2], sys.argv[3]
STILLS = None
if "--stills" in sys.argv:
    STILLS = [float(x) for x in sys.argv[sys.argv.index("--stills") + 1].split(",")]

W, H, FPS = 1080, 1920, 30
CX = 520  # axe central de la zone sûre TikTok
INK, RED, RED_D, W_, GREY = (7, 3, 3), (232, 38, 43), (142, 18, 22), (244, 241, 236), (138, 133, 128)
CASE_VIDE = (58, 37, 38)

with wave.open(VOIX) as wf:
    FIN_VOIX = wf.getnframes() / wf.getframerate()
CTA = 2.0  # secondes tenues sur la fin « COMMENTE GO » après la voix (même valeur dans synth.py)
DUREE = FIN_VOIX + CTA
NF = int(round(DUREE * FPS))

# ---------- mots ----------
brut = [w for w in json.load(open(os.path.join(ICI, "mots.json")))["words"] if w["type"] == "word"]
MOTS = []
i = 0
while i < len(brut):
    w = brut[i]
    if w["text"] == "deux" and i + 2 < len(brut) and brut[i + 1]["text"] == "K":
        MOTS.append({"t": "2K25,", "s": w["start"], "e": brut[i + 2]["end"]})
        i += 3
        continue
    MOTS.append({"t": w["text"], "s": w["start"], "e": w["end"]})
    i += 1
def at(txt, n=1):
    """Instant du n-ième mot qui commence par txt."""
    k = 0
    for m in MOTS:
        if m["t"].lower().strip(".,").startswith(txt.lower()):
            k += 1
            if k == n:
                return m["s"]
    raise KeyError(txt)

# ---------- polices ----------
_fc = {}
def px(size):
    k = ("px", size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(os.path.join(POLICES, "silkscreen-latin-700-normal.woff"), size)
    return _fc[k]
def pop(size):
    k = ("pop", size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(os.path.join(POLICES, "poppins-latin-800-normal.woff"), size)
    return _fc[k]

# ---------- sprites ----------
PAL = {"w": W_, "r": RED, "d": RED_D, "k": (20, 16, 16), "g": GREY, "s": (201, 194, 186),
       "p": (240, 138, 154), "y": (242, 196, 109), "b": (94, 107, 255), "m": (58, 52, 51)}
CARTE = [
    ".......rr..rr.......",
    "........rrrr........",
    "wwwwwwwwwrrwwwwwwwww",
    "wwwwwwwwwrrwwwwwwwww",
    "wwwwwwwwwrrwwwwwwwww",
    "rrrrrrrrrrrrrrrrrrrr",
    "dddddddddrrddddddddd",
    "wwwwwwwwwrrwwwwwwwww",
    "wggggwwwwrrwwwwwwwww",
    "wwwwwwwwwrrwwwgggggw",
    "wwwwwwwwwrrwwwwwwwww",
    "gggggggggggggggggggg",
]
BILLET = ["rrrrrrrrrrrrrr", "rwwwwwwwwwwwwr", "rwrrrrwwrrrrwr", "rwrrrwrrwrrrwr",
          "rwrrrrwwrrrrwr", "rwwwwwwwwwwwwr", "rrrrrrrrrrrrrr"]
for s in (CARTE, BILLET):
    assert len({len(l) for l in s}) == 1, s

_sc = {}
def sprite(rows, n):
    k = (id(rows), n)
    if k not in _sc:
        im = Image.new("RGBA", (len(rows[0]) * n, len(rows) * n), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for y, l in enumerate(rows):
            for x, c in enumerate(l):
                if c != ".":
                    d.rectangle([x * n, y * n, x * n + n - 1, y * n + n - 1], fill=PAL[c] + (255,))
        _sc[k] = im
    return _sc[k]

# ---------- briques ----------
def apparition(t, t0):
    """Échelle 0,5 -> 1 en 4 paliers sur 0,16 s. None si pas encore là."""
    if t < t0:
        return None
    k = min(4, int((t - t0) / 0.04) + 1)
    return 0.5 + 0.5 * k / 4

def coller(fond, el, cx, cy, ech=1.0, rot=0):
    if ech is None:
        return
    if ech != 1.0:
        el = el.resize((max(1, int(el.width * ech)), max(1, int(el.height * ech))), Image.NEAREST)
    if rot:
        el = el.rotate(rot, resample=Image.NEAREST, expand=True)
    fond.alpha_composite(el, (int(cx - el.width / 2), int(cy - el.height / 2)))

def texte_img(txt, font, col, interligne=1.05):
    lignes = txt.split("\n")
    hl = int(font.size * interligne)
    larg = max(int(font.getlength(l)) for l in lignes)
    im = Image.new("RGBA", (larg + 4, hl * len(lignes) + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for j, l in enumerate(lignes):
        lw = font.getlength(l)
        d.text(((larg - lw) / 2, j * hl), l, font=font, fill=col)
    return im

def tag(txt, size, fond_col, txt_col):
    f = px(size)
    lw = int(f.getlength(txt))
    im = Image.new("RGBA", (lw + 28, size + 18), fond_col + (255,))
    ImageDraw.Draw(im).text((14, 4), txt, font=f, fill=txt_col)
    return im

def tampon(txt, size):
    f = px(size)
    lw = int(f.getlength(txt))
    w, h = lw + 60, size + 50
    im = Image.new("RGBA", (w, h), (7, 3, 3, 217))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w - 1, h - 1], outline=RED, width=6)
    d.text((30, 20), txt, font=f, fill=RED)
    return im.rotate(8, resample=Image.NEAREST, expand=True)

def coller_tampon(fond, txt, size, cx, cy, t, t0):
    if t < t0:
        return
    k = min(3, int((t - t0) / 0.04))
    ech = [1.6, 1.4, 1.2, 1.0][k]
    coller(fond, tampon(txt, size), cx, cy, ech)

def fenetre(titre, larg, haut, barre=RED, titre_col=W_):
    im = Image.new("RGBA", (larg + 48, haut + 48), (0, 0, 0, 0))
    # lueur rouge simple, par paliers (pas de flou)
    d = ImageDraw.Draw(im)
    for k, a in ((20, 18), (12, 30), (4, 255)):
        col = (232, 38, 43, a) if k > 4 else INK + (255,)
        d.rectangle([24 - k, 24 - k, 24 + larg + k - 1, 24 + haut + k - 1], fill=col)
    d.rectangle([24, 24, 24 + larg - 1, 24 + haut - 1], fill=(7, 3, 3, 235), outline=barre, width=4)
    d.rectangle([24, 24, 24 + larg - 1, 24 + 56], fill=barre)
    d.text((24 + 20, 24 + 12), titre, font=px(30), fill=titre_col)
    for j in range(3):
        x = 24 + larg - 30 - j * 22
        d.rectangle([x, 24 + 22, x + 11, 24 + 33], fill=titre_col)
    return im

def ligne(txt, size, t, t0, col):
    """Carré plein + texte qui s'écrit en 0,45 s."""
    f = px(size)
    n = max(0, min(len(txt), int((t - t0) / 0.45 * len(txt)) + 1))
    c = int(size * 0.75)
    im = Image.new("RGBA", (int(f.getlength(txt)) + c + 24, size + 10), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 6, c, 6 + c], fill=RED)
    d.text((c + 18, 0), txt[:n], font=f, fill=col)
    return im

def jauge(label, t, t0):
    f = px(40)
    im = Image.new("RGBA", (420 + 10 * 31, 50), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((0, 2), label, font=f, fill=W_)
    plein = max(0, min(10, int((t - t0) / 0.04)))
    for j in range(10):
        x = 420 + j * 31
        d.rectangle([x, 4, x + 25, 43], fill=RED if j < plein else CASE_VIDE)
    return im

# ---------- décor ----------
def fond_fixe():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    # halo : ellipse à 50% / 52%, rayon de l'ellipse = coin le plus loin (farthest-corner)
    rx, ry = W * 0.5 * math.sqrt(2), H * 0.52 * math.sqrt(2)
    r = np.sqrt(((x - W * 0.5) / rx) ** 2 + ((y - H * 0.52) / ry) ** 2)
    stops = [(0, (120, 12, 14, .55)), (.40, (50, 6, 8, .35)), (.72, (7, 3, 3, 0))]
    img = np.zeros((H, W, 3), np.float32) + np.array(INK, np.float32)
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        m = (r >= p0) & (r < p1)
        u = ((r - p0) / (p1 - p0))[m][:, None]
        col = np.array(c0[:3]) * (1 - u) + np.array(c1[:3]) * u
        a = c0[3] * (1 - u) + c1[3] * u
        img[m] = img[m] * (1 - a) + col * a
    return Image.fromarray(img.clip(0, 255).astype(np.uint8)).convert("RGBA")

FOND = fond_fixe()
_sl = np.zeros((H, W, 4), np.uint8)
_sl[(np.arange(H) % 4) < 2, :, 3] = 31
BALAYAGE = Image.fromarray(_sl, "RGBA")

rng = np.random.default_rng(7)
POUSS = [dict(x=rng.uniform(0, W), y=rng.uniform(0, H), v=rng.uniform(15, 45), s=6 if k % 9 == 0 else 3,
              rouge=k % 4 != 3, ph=rng.uniform(0, 6)) for k in range(40)]
PLUIE = [dict(x=rng.uniform(60, 1020), y0=rng.uniform(-1900, 0), v=rng.uniform(260, 480),
              rot=int(rng.integers(-3, 4)) * 10, carte=k % 2 == 0) for k in range(14)]

def poussieres(img, t):
    d = ImageDraw.Draw(img)
    for p in POUSS:
        y = (p["y"] + p["v"] * t) % H
        if math.floor(t * 3 + p["ph"]) % 4 == 0:
            continue  # scintille
        col = (232, 38, 43, 89) if p["rouge"] else (244, 241, 236, 64)
        d.rectangle([p["x"], y, p["x"] + p["s"] - 1, y + p["s"] - 1], fill=col)

def pluie(img, t, t0):
    """Cartes cadeaux et billets qui tombent (décor) ; s'effacent à 10 % sur la bande des sous-titres."""
    if t < t0:
        return
    for p in PLUIE:
        y = p["y0"] + p["v"] * (t - t0)
        if y > H + 100:
            continue
        el = sprite(CARTE, 5) if p["carte"] else sprite(BILLET, 6)
        rot = p["rot"] + int(math.sin(t * 2 + p["x"]) * 2) * 10
        el = el.rotate(rot, resample=Image.NEAREST, expand=True)
        a = 0.10 if 1150 < y < 1420 else 0.85
        el = el.copy()
        el.putalpha(el.getchannel("A").point(lambda v: int(v * a)))
        img.alpha_composite(el, (int(p["x"] - el.width / 2), int(y - el.height / 2)))

def explosion(img, t, t0, cx, cy):
    if not (t0 <= t < t0 + 0.6):
        return
    k = int((t - t0) / 0.05)  # paliers
    d = ImageDraw.Draw(img)
    for j in range(16):
        ang = j * math.pi / 8 + (j % 2) * 0.2
        dist = 60 + k * 38 + (j % 3) * 20
        s = max(6, 24 - k * 2)
        x, y = cx + math.cos(ang) * dist * 1.2, cy + math.sin(ang) * dist * 0.8
        d.rectangle([x, y, x + s, y + s], fill=RED if j % 3 else W_)

# ---------- scènes (calées sur les mots) ----------
TEL = [
    ".wwwwwwwww.",
    "wkkkkkkkkkw",
    "wkkkmmmkkkw",
    "wdddddddddw",
    "wdrrdwwdyyw",
    "wdrrdwwdyyw",
    "wdddddddddw",
    "wdppdbbdrrw",
    "wdppdbbdrrw",
    "wdddddddddw",
    "wdwwdrrdppw",
    "wdwwdrrdppw",
    "wdddddddddw",
    "wdddddddddw",
    "wdddddddddw",
    "wkkkkkkkkkw",
    "wkkkkwkkkkw",
    "wkkkkkkkkkw",
    ".wwwwwwwww.",
]
INTER = ["..wwwww..", ".ww...ww.", ".ww...ww.", "......ww.", "....www..", "....ww...", "....ww...", ".........", "....ww...", "....ww..."]
assert len({len(l) for l in TEL}) == 1 and len({len(l) for l in INTER}) == 1

def coupe(mot, n=1):
    return at(mot, n) - 0.15  # une scène change 0,15 s avant sa phrase
C2, C4, C5, C6, C7 = coupe("chaque"), coupe("tu"), coupe("et"), coupe("ou"), coupe("c'est")
T_CTA = coupe("écris")
T_TEL = at("iphone") - 0.08
GLITCHS = [0.0, C2, C4, C5, T_TEL, C6, C7, at("pas") - 0.08, T_CTA]

def scene1(img, t):
    coller(img, tag("LES GARS", 52, W_, INK), CX, 370, apparition(t, -0.2))
    coller(img, texte_img("TECH APPLE", px(90), W_), CX, 530, apparition(t, -0.2))
    coller(img, texte_img("2K25", px(220), RED), CX, 720, apparition(t, -0.2))
    coller_tampon(img, "PERSONNE N'EN PARLE", 44, CX, 990, t, at("personne") - 0.08)

STOPS = [at("carte") - 0.08 + k * 0.14 for k in range(3)]
def scene2(img, t):
    """Tirage du jour : 3 cases qui défilent puis s'arrêtent sur la carte cadeau."""
    coller(img, tag("CHAQUE JOUR", 56, RED, W_), CX, 370, apparition(t, C2 + 0.07))
    win = fenetre("TIRAGE DU JOUR", 800, 300)
    d = ImageDraw.Draw(win)
    icones = [sprite(CARTE, 9), sprite(BILLET, 12), sprite(INTER, 16)]
    for k in range(3):
        x0, y0 = 24 + 26 + k * 254, 24 + 84
        d.rectangle([x0, y0, x0 + 234, y0 + 200], outline=W_, width=5)
        ic = icones[0] if t >= STOPS[k] else icones[int(t / 0.08 + k) % 3]
        if t >= STOPS[k]:
            d.rectangle([x0 + 5, y0 + 5, x0 + 229, y0 + 195], fill=(59, 16, 18))
        win.alpha_composite(ic, (x0 + 117 - ic.width // 2, y0 + 100 - ic.height // 2))
    coller(img, win, CX, 680, apparition(t, C2 + 0.1))
    if t >= STOPS[2] + 0.2 and (math.floor(t * 4) % 2 == 0 or t < STOPS[2] + 0.36):
        coller(img, tag("GAGNÉ !", 64, W_, INK), CX, 960, apparition(t, STOPS[2] + 0.2))

def scene4(img, t):
    """On cumule : un jour de plus toutes les 0,12 s, la cagnotte se remplit."""
    coller(img, tag("JOUR APRÈS JOUR", 52, W_, INK), CX, 370, apparition(t, C4 + 0.07))
    t0 = at("cumules") - 0.08
    jour = 1 + max(0, int((t - t0) / 0.12))
    win = fenetre("CAGNOTTE", 800, 300)
    win.alpha_composite(texte_img(f"JOUR {jour}", px(96), W_), (24 + 40, 24 + 90))
    d = ImageDraw.Draw(win)
    plein = max(0, min(10, int((t - t0) / 0.2)))  # une case toutes les 0,2 s
    for j in range(10):
        x = 24 + 40 + j * 72
        d.rectangle([x, 24 + 230, x + 60, 24 + 280], fill=RED if j < plein else CASE_VIDE)
    coller(img, win, CX, 680, apparition(t, C4 + 0.1))
    coller_tampon(img, "0 € PAYÉ", 80, CX, 1040, t, at("sans") - 0.08)

def scene5(img, t):
    coller(img, tag("QUELQUES MOIS PLUS TARD", 40, W_, INK), CX, 370, apparition(t, C5 + 0.07))
    if t < T_TEL:  # le temps passe : sablier de points
        n = int((t - C5) / 0.25) % 4
        coller(img, texte_img("." * n, px(200), RED), CX, 600)
        coller(img, jauge("CAGNOTTE", t, C5 + 0.2), CX, 900, apparition(t, C5 + 0.1))
    s = apparition(t, T_TEL)
    if s and t > T_TEL + 0.4:
        s *= 1.0 + 0.06 * (math.floor(t * 4) % 2)
    coller(img, sprite(TEL, 20), CX, 690, s, int(round(math.sin(t * 3) * 2)) * 3)
    explosion(img, t, T_TEL, CX, 690)
    coller_tampon(img, "IPHONE GRATUIT", 60, CX, 1070, t, at("gratuit") - 0.08)

L1, L2, L3 = at("t'achètes") - 0.08, at("sur") - 0.08, at("revends") - 0.08
def scene6(img, t):
    coller(img, tag("OU ALORS", 56, W_, INK), CX, 370, apparition(t, C6 + 0.07))
    win = fenetre("MODE D'EMPLOI", 800, 330)
    for k, (txt, t0, col) in enumerate((("ACHÈTE CE QUE TU VEUX", L1, W_),
                                         ("SUR LE SITE APPLE", L2, W_),
                                         ("REVENDS", L3, RED))):
        if t >= t0:
            win.alpha_composite(ligne(txt, 40, t, t0, col), (24 + 24, 24 + 92 + k * 78))
    coller(img, win, CX, 650, apparition(t, C6 + 0.1))
    if t >= L3:
        coller(img, jauge("REVENTE", t, L3 + 0.1), CX, 960, apparition(t, L3))
        if t > L3 + 0.5 and math.floor(t * 4) % 2 == 0:
            coller(img, tag("ENCAISSÉ", 44, RED, W_), CX, 1060)

def scene7(img, t):
    s = apparition(t, C7)
    coller(img, texte_img("C'EST UNE", px(80), W_), CX, 470, s)
    coller(img, texte_img("DINGUERIE", px(100), RED), CX, 580, s)
    coller(img, sprite(CARTE, 16), CX, 800, s, int(round(math.sin(t * 3) * 3)) * 3)
    coller_tampon(img, "PAS PLUS SIMPLE", 58, CX, 1050, t, at("pas") - 0.08)

def bloc(lignes_txt, size, fond_col, txt_col):
    f = px(size)
    lw = max(int(f.getlength(l)) for l in lignes_txt)
    hl = int(size * 1.15)
    im = Image.new("RGBA", (lw + 36, hl * len(lignes_txt) + 22), fond_col + (255,))
    d = ImageDraw.Draw(im)
    for j, l in enumerate(lignes_txt):
        d.text(((lw + 36 - f.getlength(l)) / 2, 10 + j * hl), l, font=f, fill=txt_col)
    return im

def scene8(img, t):
    """CTA : commente « GO » et je t'accompagne gratuitement."""
    coller(img, tag("EN COMMENTAIRE", 52, W_, INK), CX, 350, apparition(t, T_CTA))
    coller(img, texte_img("COMMENTE", px(100), W_), CX, 480, apparition(t, T_CTA))
    t_go = at("go") - 0.08
    s = apparition(t, t_go)
    if s and t > t_go + 0.4:  # « GO » qui bat, par demi-paliers
        s *= 1.0 + 0.12 * (math.floor(t * 4) % 2)
    coller(img, texte_img("« GO »", px(150), RED), CX, 645, s)
    win = fenetre("COMMENTAIRE", 800, 150, barre=W_, titre_col=INK)
    d = ImageDraw.Draw(win)
    n = 0 if t < t_go + 0.3 else min(2, int((t - t_go - 0.3) / 0.12) + 1)
    f = px(56)
    d.text((24 + 30, 24 + 76), "GO"[:n], font=f, fill=W_)
    if math.floor(t * 5) % 2 == 0:
        x = 24 + 30 + f.getlength("GO"[:n]) + 8
        d.rectangle([x, 24 + 80, x + 26, 24 + 132], fill=RED)
    coller(img, win, CX, 860, apparition(t, T_CTA + 0.1))
    coller(img, bloc(["JE T'ACCOMPAGNE", "GRATUITEMENT"], 52, RED, W_), CX, 1085,
           apparition(t, at("t'accompagne") - 0.08))

SCENES = [(C2, scene1), (C4, scene2), (C5, scene4), (C6, scene5), (C7, scene6),
          (T_CTA, scene7), (DUREE + 1, scene8)]

# ---------- sous-titres ----------
ROUGES = {"apple", "2k25", "cadeau", "chance", "gratuitement", "gratuit", "iphone",
          "revends", "dinguerie", "simple", "go"}
COUPES = [2, 4, 3, 2, 5, 4, 5, 3, 3, 3, 6, 2, 5, 4, 3, 3, 4, 4, 4]  # mots par morceau (6 max)
MORCEAUX, k = [], 0
for n in COUPES:
    MORCEAUX.append(MOTS[k:k + n])
    k += n
assert k == len(MOTS), (k, len(MOTS))

def sous_titres(img, t):
    for j, m in enumerate(MORCEAUX):
        debut = m[0]["s"] - 0.08
        fin = MORCEAUX[j + 1][0]["s"] - 0.08 if j + 1 < len(MORCEAUX) else DUREE
        fin = min(fin, m[-1]["e"] + 0.7)
        if not (debut <= t < fin):
            continue
        f = pop(60)
        esp = f.getlength(" ")
        # coupe en 2 lignes si plus large que 800 px
        larg = [f.getlength(w["t"]) for w in m]
        tot = sum(larg) + esp * (len(m) - 1)
        lignes = [m]
        if tot > 800:
            acc, c = 0, 0
            for c, l in enumerate(larg):
                acc += l + esp
                if acc > tot / 2:
                    break
            lignes = [m[:c + 1], m[c + 1:]] if c + 1 < len(m) else [m[:c], m[c:]]
        d = ImageDraw.Draw(img)
        y0 = 1288 - 36 * len(lignes)
        for li, lm in enumerate(lignes):
            lw = sum(f.getlength(w["t"]) for w in lm) + esp * (len(lm) - 1)
            x = CX - lw / 2
            for w in lm:
                if t >= w["s"] - 0.08:
                    col = RED if w["t"].lower().strip(".,") in ROUGES else W_
                    d.text((x, y0 + li * 72), w["t"], font=f, fill=col, stroke_width=5, stroke_fill=INK)
                x += f.getlength(w["t"]) + esp

# ---------- image ----------
def image(t):
    img = FOND.copy()
    poussieres(img, t)
    for fin, scene in SCENES:
        if t < fin:
            if scene is scene7:
                pluie(img, t, C7 + 0.3)
            scene(img, t)
            break
    sous_titres(img, t)
    img.alpha_composite(BALAYAGE)
    for g in GLITCHS:
        if g <= t < g + 0.15:
            dx = int(math.sin(t * 97) * 8) or 6
            sh = Image.new("RGBA", (W, H), INK + (255,))
            sh.paste(img, (dx, 0))
            # bande décalée façon glitch
            yb = int(300 + (g * 997) % 1100)
            bande = img.crop((0, yb, W, yb + 60))
            sh.paste(bande, (dx * 3, yb))
            img = sh
            break
    return img.convert("RGB")

if STILLS:
    for s in STILLS:
        image(s).save(os.path.join(os.path.dirname(SORTIE), f"still-{s:05.2f}.png"))
    sys.exit()

AUDIO = os.path.join(os.path.dirname(SORTIE), "mix.wav")
cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
       "-i", "-", "-i", AUDIO, "-c:v", "libx264", "-preset", "slow", "-b:v", "10M", "-maxrate", "12M",
       "-bufsize", "20M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
       "-movflags", "+faststart", SORTIE]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for n in range(NF):
    p.stdin.write(image(n / FPS).tobytes())
p.stdin.close()
p.wait()
