"""Tech Apple 2K25, « le jeu en 3 niveaux » — DA pixel noir et rouge, 1080x1920, 30 i/s, calée sur la voix ElevenLabs (texte.txt).

Usage : python3 rendu.py <voix.wav> <dossier_polices> <sortie.mp4> [--stills t1,t2,...]
Les instants des mots viennent de mots.json (transcription mot à mot de la voix).
"""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tag_marque import tag_mobile, signature  # tag anti-copie (videos/marque.json)

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
PC = [
    "wwwwwwwwwwwwww",
    "wddddddddddddw",
    "wdrrddwwddyydw",
    "wdrrddwwddyydw",
    "wddddddddddddw",
    "wdppddbbddrrdw",
    "wdppddbbddrrdw",
    "wddddddddddddw",
    "wwwwwwwwwwwwww",
    ".....wwww.....",
    "....wwwwww....",
    "..wwwwwwwwww..",
]
for s_ in (TEL, PC):
    assert len({len(l) for l in s_}) == 1

def coupe(mot, n=1):
    return at(mot, n) - 0.15  # une scène change 0,15 s avant sa phrase
T_CTA = coupe("commente", 2)  # le 1er « commentes » est au niveau 3

def bat(s, t, t0, amp=0.08, f=6):
    """Pulsation par demi-paliers après t0."""
    if s and t > t0:
        s *= 1.0 + amp * (math.floor(t * f) % 2)
    return s

# --- briques de scène (chacune reçoit ses instants) ---
def s_iphone(img, t, t_app, t_gratuit):
    """L'iPhone 18 Pro qui tombe avec une explosion, puis le tampon GRATUIT."""
    coller(img, tag("IPHONE 18 PRO", 56, RED, W_), CX, 370, apparition(t, t_app))
    s = bat(apparition(t, t_app), t, t_app + 0.4, 0.05, 4)
    coller(img, sprite(TEL, 20), CX, 670, s, int(round(math.sin(t * 3) * 2)) * 3)
    explosion(img, t, t_app, CX, 670)
    coller_tampon(img, "GRATUIT", 96, CX, 990, t, t_gratuit - 0.08)

def s_tech(img, t, t_app, t_2k25, haut=None):
    """TECH APPLE / 2K25, avec une étiquette en haut (texte, instant) et l'explosion sur 2K25."""
    if haut:
        txt, t_h, fond_col, txt_col = haut
        coller(img, tag(txt, 48, fond_col, txt_col), CX, 370, apparition(t, t_h))
    coller(img, texte_img("TECH APPLE", px(90), W_), CX, 530, apparition(t, t_app))
    s = bat(apparition(t, t_2k25 - 0.08), t, t_2k25 + 0.3, 0.04)
    coller(img, texte_img("2K25", px(220), RED), CX, 720, s)
    explosion(img, t, t_2k25, CX, 720)

def case_cochee(txt, size, t, t0):
    """Case blanche + coche rouge en 3 paliers (cochée à t0) ; le texte est toujours là."""
    f = px(size)
    c = size
    im = Image.new("RGBA", (int(f.getlength(txt)) + c + 30, c + 12), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 4, c, 4 + c], outline=W_, width=5)
    if t >= t0:
        k = min(3, int((t - t0) / 0.05) + 1)
        u = c / 8
        coche = [(1.5, 4.5), (2.5, 5.5), (3.5, 6.5), (4.5, 5.5), (5.5, 4.5), (6.5, 3.5), (7.5, 2.5)]
        for x, y in coche[: [0, 3, 5, 7][k]]:
            d.rectangle([x * u - u, 4 + y * u - u, x * u + u, 4 + y * u + u], fill=RED)
    d.text((c + 24, 2), txt, font=f, fill=W_ if t >= t0 else GREY)
    return im

def s_conditions(img, t, t_app, haut=("LES CONDITIONS", RED, W_)):
    """Check-list : majeur, un PC, ou un iPhone — chaque case se coche sur son mot."""
    txt, fond_col, txt_col = haut
    coller(img, tag(txt, 52, fond_col, txt_col), CX, 370, apparition(t, t_app))
    win = fenetre("CHECK-LIST", 800, 300)
    for k, (ligne_txt, mot) in enumerate((("MAJEUR", "majeur"), ("UN PC", "pc"), ("OU UN IPHONE", "iphone"))):
        win.alpha_composite(case_cochee(ligne_txt, 52, t, at(mot) - 0.08), (24 + 34, 24 + 86 + k * 72))
    coller(img, win, CX, 640, apparition(t, t_app + 0.03))
    coller(img, sprite(PC, 12), CX - 200, 1010, apparition(t, at("pc") - 0.08))
    coller(img, texte_img("OU", px(64), RED), CX, 1010, apparition(t, at("ou") - 0.08))
    coller(img, sprite(TEL, 9), CX + 200, 1010, apparition(t, at("iphone") - 0.08),
           int(round(math.sin(t * 3) * 2)) * 3)

def s_texte(img, t, t_app, haut, bas, taille_bas, tampon=None, sprite_carte=False):
    """Grand texte sur 2 lignes (blanc puis rouge), un tampon optionnel (texte, taille, instant)."""
    s = apparition(t, t_app)
    taille_haut = min(100, int(800 / (0.81 * len(haut))))  # tient dans les 800 px de la zone sûre
    coller(img, texte_img(haut, px(taille_haut), W_), CX, 470, s)
    coller(img, texte_img(bas, px(taille_bas), RED), CX, 470 + 60 + taille_bas // 2 + 10, bat(s, t, t_app + 0.5, 0.04))
    if tampon:
        coller_tampon(img, tampon[0], tampon[1], CX, 900, t, tampon[2])

def bloc(lignes_txt, size, fond_col, txt_col):
    f = px(size)
    lw = max(int(f.getlength(l)) for l in lignes_txt)
    hl = int(size * 1.15)
    im = Image.new("RGBA", (lw + 36, hl * len(lignes_txt) + 22), fond_col + (255,))
    d = ImageDraw.Draw(im)
    for j, l in enumerate(lignes_txt):
        d.text(((lw + 36 - f.getlength(l)) / 2, 10 + j * hl), l, font=f, fill=txt_col)
    return im

def s_cta(img, t):
    """CTA : commente « GO » et je t'accompagne gratuitement."""
    coller(img, tag("EN COMMENTAIRE", 52, W_, INK), CX, 350, apparition(t, T_CTA))
    coller(img, texte_img("COMMENTE", px(100), W_), CX, 480, apparition(t, T_CTA))
    t_go = at("go", 2) - 0.08
    coller(img, texte_img("« GO »", px(150), RED), CX, 645, bat(apparition(t, t_go), t, t_go + 0.4, 0.12, 4))
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

def rappel_cta(img, t, t0):
    """Petit rappel « COMMENTE GO » au-dessus des sous-titres, de t0 jusqu'au CTA final."""
    if t0 <= t < T_CTA:
        coller(img, tag("COMMENTE GO", 40, W_, INK), CX, 1165, apparition(t, t0))

# --- le jeu en 3 niveaux ---
COFFRE = [
    ".wwwwwwwwww.",
    "wddddddddddw",
    "wddddddddddw",
    "wwwwwwwwwwww",
    "wddddrrddddw",
    "wddddrrddddw",
    "wddddddddddw",
    "wddddddddddw",
    "wwwwwwwwwwww",
]
assert len({len(l) for l in COFFRE}) == 1

C2, C3, C4 = coupe("niveau", 2), coupe("niveau", 3), coupe("niveau", 4)  # « niveaux » est le 1er
C5, C6 = at("récompense") - 0.08, coupe("l'iphone")  # le niveau 3 tient jusqu'à « récompense »
V1, V2 = at("majeur") + 0.4, at("iphone") + 0.4
GO3 = at("go") - 0.08  # le « go » du niveau 3

def progression(img, t, de, a, t0):
    """Barre PROGRESSION de 10 cases : passe de `de` à `a` cases à partir de t0 ; la case suivante clignote."""
    f = px(40)
    im = Image.new("RGBA", (420 + 10 * 31, 50), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((0, 2), "PROGRESSION", font=f, fill=W_)
    plein = de if t < t0 else min(a, de + int((t - t0) / 0.06) + 1)
    for j in range(10):
        x = 420 + j * 31
        col = RED if j < plein else CASE_VIDE
        if j == plein and math.floor(t * 4) % 2 == 0:
            col = W_
        d.rectangle([x, 4, x + 25, 43], fill=col)
    coller(img, im, CX, 1080)

def s_titre(img, t):
    s_tech(img, t, -0.2, -0.1, ("LE JEU", -0.2, W_, INK))
    coller_tampon(img, "3 NIVEAUX", 80, CX, 990, t, at("trois") - 0.08)

def s_niveau1(img, t):
    coller(img, tag("NIVEAU 1", 56, RED, W_), CX, 370, apparition(t, C2))
    coller(img, texte_img("T'ES", px(90), W_), CX, 520, apparition(t, at("t'es") - 0.08))
    coller(img, texte_img("MAJEUR", px(150), RED), CX, 660, apparition(t, at("majeur") - 0.08))
    coller_tampon(img, "VALIDÉ", 90, CX, 900, t, V1)
    progression(img, t, 0, 3, V1)

def s_niveau2(img, t):
    coller(img, tag("NIVEAU 2", 56, RED, W_), CX, 370, apparition(t, C3))
    coller(img, texte_img("T'AS", px(90), W_), CX, 500, apparition(t, at("t'as") - 0.08))
    coller(img, sprite(PC, 14), CX - 210, 690, apparition(t, at("pc") - 0.08))
    coller(img, texte_img("OU", px(80), RED), CX, 690, apparition(t, at("ou") - 0.08))
    coller(img, sprite(TEL, 11), CX + 220, 690, apparition(t, at("iphone") - 0.08),
           int(round(math.sin(t * 3) * 2)) * 3)
    coller_tampon(img, "VALIDÉ", 90, CX, 920, t, V2)
    progression(img, t, 3, 6, V2)

def s_niveau3(img, t):
    """Le dernier niveau, c'est le spectateur qui le joue."""
    coller(img, tag("NIVEAU 3", 56, RED, W_), CX, 370, apparition(t, C4))
    coller(img, texte_img("TU COMMENTES", px(70), W_), CX, 500, apparition(t, at("tu", 2) - 0.08))
    win = fenetre("COMMENTAIRE", 800, 150, barre=W_, titre_col=INK)
    d = ImageDraw.Draw(win)
    n = 0 if t < GO3 else min(2, int((t - GO3) / 0.12) + 1)
    f = px(56)
    d.text((24 + 30, 24 + 76), "GO"[:n], font=f, fill=W_)
    if math.floor(t * 5) % 2 == 0:
        x = 24 + 30 + f.getlength("GO"[:n]) + 8
        d.rectangle([x, 24 + 80, x + 26, 24 + 132], fill=RED)
    coller(img, win, CX, 680, apparition(t, C4 + 0.1))
    coller_tampon(img, "À TOI DE JOUER", 56, CX, 920, t, GO3 + 0.2)
    progression(img, t, 6, 9, GO3 + 0.2)

def s_recompense(img, t):
    """Le coffre qui tremble avant la révélation."""
    coller(img, tag("RÉCOMPENSE", 56, W_, INK), CX, 370, apparition(t, C5 + 0.05))
    rot = (10 if int(t * 12) % 2 else -10) if t > C5 + 0.3 else 0
    halo_r = 120 + (math.floor(t * 6) % 2) * 16
    d = ImageDraw.Draw(img)
    d.ellipse([CX - halo_r * 1.6, 680 - halo_r, CX + halo_r * 1.6, 680 + halo_r], fill=(232, 38, 43, 40))
    coller(img, sprite(COFFRE, 24), CX, 680, apparition(t, C5 + 0.05), rot)
    coller(img, texte_img("?", px(160), RED), CX, 980, bat(apparition(t, at("récompense")), t, 0, 0.12, 4))

SCENES = [
    (C2, s_titre),
    (C3, s_niveau1),
    (C4, s_niveau2),
    (C5, s_niveau3),
    (C6, s_recompense),
    (T_CTA, lambda img, t: s_iphone(img, t, C6 + 0.1, at("gratuit"))),
]
RAPPEL = C5
GLITCHS = [0.0, C2, V1, C3, V2, C4, C5, C6, T_CTA]
SCENES = [(fin, fn, None) for fin, fn in SCENES] + [(DUREE + 1, s_cta, None)]

# ---------- sous-titres ----------
ROUGES = {"apple", "2k25", "dinguerie", "explose", "majeur", "pc", "iphone", "l'iphone", "18", "pro", "gratuit",
          "simple", "go", "gratuitement", "tout", "toi", "niveau", "validé", "récompense?", "majeur.", "commentes"}
# morceaux de 5 mots au plus, coupés à la ponctuation
COUPES, n = [], 0
for w in MOTS:
    n += 1
    if n == 5 or w["t"][-1] in ".,?!:":
        COUPES.append(n)
        n = 0
if n:
    COUPES.append(n)
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
    for fin, scene, t_pluie in SCENES:
        if t < fin:
            if t_pluie is not None:
                pluie(img, t, t_pluie)
            scene(img, t)
            break
    rappel_cta(img, t, RAPPEL)
    police_px = os.path.join(POLICES, "silkscreen-latin-700-normal.woff")
    tag_mobile(img, t, police_px, T_CTA)
    signature(img, t, police_px, at("t'accompagne") + 0.3)
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
