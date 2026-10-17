"""Astuces iPhone sans visage — 5 vidéos en motion design (iPhone dessiné, générique, sans logo).

Usage : python3 astuces.py <voix.wav> <dossier_polices> <sortie.mp4> --video 1..5 [--stills t1,...] [--timeline f.json]
  1 « Bouton caché »   : Toucher le dos (Réglages > Accessibilité > Toucher > Toucher le dos).
  2 « Clavier »        : appui long sur la barre d'espace = trackpad.
  3 « 3 réglages »     : actualisation en arrière-plan, services système, analyses.
  4 « Texte en direct »: l'appareil photo lit le texte (mot de passe Wi-Fi).
  5 « Avis tranché »   : changer d'iPhone chaque année ?
Les instants des mots viennent de mots_<video>.json ; le son de out/mix.wav (synth_astuces.py).
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
CX = 520
NOIR, ROUGE, ROUGE_F, BLANC, GRIS = (10, 9, 11), (232, 38, 43), (120, 14, 18), (246, 243, 238), (150, 146, 150)
VERT = (52, 199, 89)
FIN_HOLD = 1.6

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
def in_out(p):
    return 3 * p * p - 2 * p * p * p
def out_expo(p):
    return 1.0 if p >= 1 else 1 - 2 ** (-10 * p)
def ressort(t, t0, freq=3.0, amort=7.0):
    x = t - t0
    return 0.0 if x <= 0 else 1 - math.exp(-amort * x) * math.cos(2 * math.pi * freq * x)

# ---------- polices, textes, formes ----------
_f = {}
def police(poids, taille):
    k = (poids, taille)
    if k not in _f:
        _f[k] = ImageFont.truetype(os.path.join(POLICES, f"poppins-latin-{poids}-normal.woff"), taille)
    return _f[k]
_c = {}
def texte(txt, taille, col=BLANC, poids=900, max_l=800):
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
        if len(_c) > 900:
            _c.clear()
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
def pilule(txt, taille, fond_col, txt_col, px=40, py=18, poids=900):
    t_im = texte(txt, taille, txt_col, poids, 800 - 2 * px)
    w, h = t_im.width + 2 * px, t_im.height + 2 * py
    im = rrect(w, h, h // 2, fond_col).copy()
    im.alpha_composite(t_im, (px, py))
    return im
DESSUS = [None]  # calque des bandeaux (au-dessus du zoom)
def bandeau(fond, txt, t, t0, cy, fond_col=ROUGE, txt_col=BLANC, taille=64):
    """Bandeau de titre (pilule) qui arrive en rebond ; dessiné sur le calque du dessus (jamais zoomé)."""
    if t < t0:
        return
    fond = DESSUS[0] if DESSUS[0] is not None else fond
    p = ressort(t, t0, 2.6, 7)
    poser(fond, pilule(txt, taille, fond_col, txt_col), CX, cy + (1 - out_expo(prog(t, t0, 0.4))) * 40, 0.7 + 0.3 * p,
          min(1, (t - t0) * 6))

# ---------- décor ----------
def _halo(r, col, a):
    y, x = np.mgrid[-r:r, -r:r].astype(np.float32)
    al = np.clip(1 - np.sqrt(x * x + y * y) / r, 0, 1) ** 2.2 * a
    return Image.fromarray(np.dstack([np.full_like(al, col[0]), np.full_like(al, col[1]), np.full_like(al, col[2]), al]).astype(np.uint8), "RGBA")
HALO = _halo(900, (190, 20, 26), 120)
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIGNETTE = Image.fromarray(np.dstack([np.zeros((H, W, 3), np.uint8),
                                      (np.clip(((_xx - W / 2) / (W * .75)) ** 2 + ((_yy - H / 2) / (H * .7)) ** 2, 0, 1) * 200).astype(np.uint8)]), "RGBA")
def decor(t):
    img = Image.new("RGBA", (W, H), NOIR + (255,))
    img.alpha_composite(HALO, (int(W / 2 - 900 + math.sin(t * .5) * 120), int(H * .45 - 900 + math.cos(t * .4) * 140)))
    img.alpha_composite(VIGNETTE)
    return img

# ---------- iPhone dessiné ----------
TEL_W = 410
TEL_H = int(TEL_W * 2.06)
INS = int(TEL_W * 0.045)
ECR_W, ECR_H = TEL_W - 2 * INS, TEL_H - 2 * INS
TEL_CX, TEL_CY = CX, 825
ECR_X0, ECR_Y0 = TEL_CX - TEL_W // 2 + INS, TEL_CY - TEL_H // 2 + INS  # coin haut gauche de l'écran sur le canevas

def _cadre():
    s = 2
    w, h = TEL_W * s, TEL_H * s
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=int(w * .17), fill=(44, 42, 46))
    d.rounded_rectangle([5, 5, w - 6, h - 6], radius=int(w * .165), fill=(16, 15, 17))
    d.rounded_rectangle([INS * s, INS * s, w - INS * s - 1, h - INS * s - 1], radius=int(w * .13), fill=(0, 0, 0, 0))
    for y0, y1, x in ((.2, .26, -3), (.28, .38, -3), (.24, .34, w - 3)):
        d.rounded_rectangle([x, h * y0, x + 6, h * y1], radius=4, fill=(70, 68, 72))
    return im.resize((TEL_W, TEL_H), Image.LANCZOS)
CADRE = _cadre()
_m = Image.new("L", (ECR_W * 2, ECR_H * 2), 0)
ImageDraw.Draw(_m).rounded_rectangle([0, 0, ECR_W * 2 - 1, ECR_H * 2 - 1], radius=int(TEL_W * .13 * 2), fill=255)
MASQUE_ECRAN = _m.resize((ECR_W, ECR_H), Image.LANCZOS)

def ilot(ecran, sombre=False):
    ImageDraw.Draw(ecran).rounded_rectangle([ECR_W * .34, 14, ECR_W * .66, 46], radius=16, fill=(0, 0, 0))

def barre_etat(ecran, col=(0, 0, 0)):
    d = ImageDraw.Draw(ecran)
    d.text((40, 18), "9:41", font=police(600, 26), fill=col)
    x = ECR_W - 80
    d.rounded_rectangle([x, 22, x + 44, 42], radius=6, outline=col, width=2)
    d.rectangle([x + 4, 26, x + 34, 38], fill=col)
    d.rectangle([x + 46, 28, x + 49, 36], fill=col)

def telephone(ecran):
    """Compose l'écran (ECR_W x ECR_H) dans le cadre."""
    im = Image.new("RGBA", (TEL_W, TEL_H), (0, 0, 0, 0))
    e = ecran.convert("RGBA")
    ilot(e)
    im.paste(e, (INS, INS), MASQUE_ECRAN)
    im.alpha_composite(CADRE)
    return im

def dos_telephone(flash=0.0):
    k = ("dos", round(flash, 2))
    if k in _c:
        return _c[k]
    s = 2
    w, h = TEL_W * s, TEL_H * s
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=int(w * .17), fill=(44, 42, 46))
    hh, ww = h - 16, w - 16
    g = np.linspace(0, 1, hh)[:, None, None]
    arr = (np.array([70, 20, 26]) * (1 - g) + np.array([28, 10, 14]) * g).astype(np.uint8)
    arr = np.repeat(arr, ww, axis=1)
    dos = Image.fromarray(np.dstack([arr, np.full((hh, ww), 255, np.uint8)]), "RGBA")
    mq = Image.new("L", dos.size, 0)
    ImageDraw.Draw(mq).rounded_rectangle([0, 0, dos.width - 1, dos.height - 1], radius=int(w * .16), fill=255)
    im.paste(dos, (8, 8), mq)
    # bloc photo générique
    bx, by, bs = int(w * .07), int(w * .07), int(w * .42)
    d.rounded_rectangle([bx, by, bx + bs, by + bs], radius=int(bs * .25), fill=(55, 18, 22), outline=(90, 40, 44), width=4)
    for (ox, oy) in ((.28, .28), (.28, .72), (.72, .5)):
        r = bs * .17
        cx, cy = bx + bs * ox, by + bs * oy
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(14, 12, 14), outline=(110, 104, 110), width=6)
        d.ellipse([cx - r * .4, cy - r * .4, cx + r * .4, cy + r * .4], fill=(40, 46, 70))
    fx, fy = bx + bs * .72, by + bs * .2
    lum = int(200 + 55 * flash)
    d.ellipse([fx - 14, fy - 14, fx + 14, fy + 14], fill=(lum, lum, int(200 * (1 - flash) + 120 * flash)))
    im = im.resize((TEL_W, TEL_H), Image.LANCZOS)
    if flash > 0.01:  # faisceau de la lampe
        g2 = Image.new("RGBA", (TEL_W, TEL_H), (0, 0, 0, 0))
        ImageDraw.Draw(g2).ellipse([fx / s - 120, fy / s - 120, fx / s + 120, fy / s + 120], fill=(255, 250, 220, int(200 * flash)))
        im.alpha_composite(g2.filter(ImageFilter.GaussianBlur(40)))
    _c[k] = im
    return im

# ---------- écrans ----------
FOND_IOS = (242, 242, 247)
GRIS_LIGNE = (198, 198, 204)
def interrupteur(on):
    """Interrupteur (on de 0 à 1, animable)."""
    w, h = 76, 46
    col = tuple(int(VERT[i] * on + (220, 220, 225)[i] * (1 - on)) for i in range(3))
    im = rrect(w, h, h // 2, col + (255,)).copy()
    k = rrect(40, 40, 20, (255, 255, 255, 255))
    im.alpha_composite(k, (int(3 + (w - 46) * on), 3))
    return im

def ecran_reglages(titre, lignes, appui=None, retour=None, entete=None, t=0.0):
    """Liste façon réglages. lignes : (libellé, couleur d'icône | None, type, valeur) ; type = 'f' (flèche),
    'i' (interrupteur, valeur 0..1), 'c' (coche, valeur bool), 'v' (texte à droite)."""
    e = Image.new("RGBA", (ECR_W, ECR_H), FOND_IOS + (255,))
    barre_etat(e)
    d = ImageDraw.Draw(e)
    y = 70
    if retour:
        d.text((24, y), "‹ " + retour, font=police(600, 28), fill=(10, 122, 255))
        y += 44
    d.text((28, y), titre, font=police(800, 42 if len(titre) < 14 else 32), fill=(0, 0, 0))
    y += 84
    if entete:
        d.text((40, y), entete.upper(), font=police(600, 20), fill=(110, 110, 115))
        y += 36
    hl = 74
    bloc = rrect(ECR_W - 40, hl * len(lignes), 22, (255, 255, 255, 255))
    e.alpha_composite(bloc, (20, y))
    for j, (lib, icol, typ, val) in enumerate(lignes):
        yy = y + j * hl
        if appui is not None and appui[0] == j and appui[1] > 0:
            a = int(255 * min(1, appui[1]))
            e.alpha_composite(rrect(ECR_W - 40, hl, 22 if j in (0, len(lignes) - 1) else 0, (209, 209, 214, a)), (20, yy))
        x = 40
        if icol:
            e.alpha_composite(rrect(40, 40, 10, icol + (255,)), (x, yy + 17))
            ImageDraw.Draw(e).rounded_rectangle([x + 12, yy + 29, x + 28, yy + 45], radius=4, fill=(255, 255, 255))
            x += 58
        taille = 27
        place = ECR_W - x - (120 if typ == "i" else (90 + police(600, 24).getlength(val or "") if typ == "v" else 70))
        f = police(600, taille)
        while f.getlength(lib) > place and taille > 16:
            taille -= 1
            f = police(600, taille)
        ImageDraw.Draw(e).text((x, yy + 20 + (27 - taille) // 2), lib, font=f, fill=(0, 0, 0))
        if typ == "f":
            ImageDraw.Draw(e).text((ECR_W - 56, yy + 16), "›", font=police(600, 36), fill=(170, 170, 176))
        elif typ == "v":
            v = police(600, 24)
            ImageDraw.Draw(e).text((ECR_W - 60 - v.getlength(val), yy + 22), val, font=v, fill=(140, 140, 146))
            ImageDraw.Draw(e).text((ECR_W - 56, yy + 16), "›", font=police(600, 36), fill=(170, 170, 176))
        elif typ == "i":
            e.alpha_composite(interrupteur(val), (ECR_W - 116, yy + 14))
        elif typ == "c" and val:
            ImageDraw.Draw(e).line([(ECR_W - 74, yy + 38), (ECR_W - 62, yy + 50), (ECR_W - 44, yy + 26)], fill=(10, 122, 255), width=5)
        if j < len(lignes) - 1:
            ImageDraw.Draw(e).line([(x, yy + hl), (ECR_W - 20, yy + hl)], fill=(225, 225, 230), width=2)
    return e

def glisse(ecran_a, ecran_b, p):
    """Transition « pousser » entre deux écrans (b arrive de la droite)."""
    if p <= 0:
        return ecran_a
    if p >= 1:
        return ecran_b
    q = in_out(p)
    e = Image.new("RGBA", (ECR_W, ECR_H), FOND_IOS + (255,))
    e.alpha_composite(ecran_a, (int(-ECR_W * 0.3 * q), 0))
    e.alpha_composite(ecran_b, (int(ECR_W * (1 - q)), 0))
    return e

# ---------- toucher (sur le canevas) ----------
def toucher(fond, x, y, t, t0, long=False):
    """Indicateur de doigt : rond blanc + onde. long : l'onde grandit et reste."""
    if t < t0 or (not long and t > t0 + 0.6):
        return
    p = prog(t, t0, 0.45)
    d = ImageDraw.Draw(fond)
    r = 34
    a = int(220 * (1 - p)) if not long else 200
    d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, a), outline=(0, 0, 0, a // 3), width=3)
    rr = r + 70 * (out_cubic(p) if not long else (0.5 + 0.5 * math.sin((t - t0) * 6)))
    d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=(255, 255, 255, int(160 * (1 - p)) if not long else 120), width=5)

def ecr(x, y):
    """Coordonnées écran -> canevas."""
    return ECR_X0 + x, ECR_Y0 + y

# ---------- sous-titres karaoké ----------
ROUGES = set()
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
        tail = 58
        f = police(900, tail)
        lw = sum(f.getlength(w["t"]) for w in m) + f.getlength(" ") * (len(m) - 1)
        while lw > 760:
            tail -= 2; f = police(900, tail)
            lw = sum(f.getlength(w["t"]) for w in m) + f.getlength(" ") * (len(m) - 1)
        y = 1300
        img.alpha_composite(rrect(lw + 60, tail + 40, (tail + 40) // 2, (10, 9, 11, 200)), (int(CX - lw / 2 - 30), int(y - 14)))
        d = ImageDraw.Draw(img)
        x = CX - lw / 2
        for w in m:
            if t >= w["s"] - 0.1:
                actif = w["s"] - 0.1 <= t < w["e"] + 0.05
                d.text((x, y), w["t"], font=f, fill=ROUGE if actif else BLANC)
            x += f.getlength(w["t"]) + f.getlength(" ")

# ---------- carte question finale ----------
def carte_question(fond, t, t0, lignes, reponse, choix=None):
    """Grande question + champ de commentaire où la réponse s'écrit (+ options en pilules)."""
    if t < t0:
        return
    for j, (l, col) in enumerate(lignes):
        p = out_expo(prog(t, t0 + j * 0.12, 0.45))
        poser(fond, texte(l, 110, col, 900), CX, 470 + j * 130 + (1 - p) * 50, 0.95 + 0.05 * ressort(t, t0 + j * .12), p)
    y_ch = 470 + len(lignes) * 130 + 60
    if choix:
        for k, c in enumerate(choix):
            tc = t0 + 0.4 + k * 0.12
            if t >= tc:
                pl = pilule(c, 52, ROUGE if k == 0 else (40, 38, 42), BLANC, 34, 14)
                poser(fond, pl, CX + (k - (len(choix) - 1) / 2) * 270, y_ch, 0.7 + 0.3 * ressort(t, tc))
        y_ch += 150
    if t >= t0 + 0.5:
        p = out_expo(prog(t, t0 + 0.5, 0.5))
        b = rrect(780, 130, 65, (34, 32, 36, 245), (255, 255, 255, 40), 2).copy()
        db = ImageDraw.Draw(b)
        db.ellipse([24, 24, 106, 106], fill=ROUGE_F)
        n = int(clamp((t - t0 - 0.9) / 0.08, 0, len(reponse)))
        txt = reponse[:n] if n else "Ajoute un commentaire..."
        b.alpha_composite(texte(txt, 44 if n else 32, BLANC if n else GRIS, 800 if n else 600, 520), (130, 40 if n else 46))
        db.ellipse([680, 25, 760, 105], fill=ROUGE if n == len(reponse) else (70, 66, 72))
        db.polygon([(702, 65), (740, 46), (728, 84)], fill=BLANC)
        poser(fond, b, CX, y_ch + (1 - p) * 60, 1, p)

# ---------- les 5 vidéos ----------
REGLAGES = [("Général", (142, 142, 147), "f", None), ("Accessibilité", (10, 122, 255), "f", None),
            ("Écran et luminosité", (10, 122, 255), "f", None), ("Batterie", VERT, "f", None),
            ("Confidentialité et sécurité", (10, 122, 255), "f", None)]
FOCUS = None  # (début, fin, zoom, x, y) : zooms caméra

def coupe(m, n=1):
    return at(m, n) - 0.15

if VIDEO == "1":  # Toucher le dos
    T_FLIP1, T_FLIP2 = at("dos") - 0.25, coupe("va")
    T_REG, T_ACC, T_TOU, T_DOS = at("réglages") - 0.1, at("accessibilité") - 0.1, at("toucher") - 0.1, at("toucher", 2) - 0.1
    T_CHO, T_CAP, T_LAM, T_APP = coupe("choisis"), at("capture") - 0.05, at("lampe") - 0.05, at("appareil") - 0.05
    T_TRI = coupe("et")
    T_Q = coupe("tu")
    def ecran_v1(t):
        reg = ecran_reglages("Réglages", REGLAGES, (1, prog(t, T_ACC - 0.25, 0.15)) if t < T_ACC + 0.1 else None)
        acc = ecran_reglages("Accessibilité", [("VoiceOver", None, "v", "Non"), ("Zoom", None, "v", "Non"),
                                                ("Toucher", None, "f", None), ("Face ID et attention", None, "f", None)],
                             (2, prog(t, T_TOU - 0.25, 0.15)) if t < T_TOU + 0.1 else None, "Réglages", "Physique et moteur")
        tou = ecran_reglages("Toucher", [("AssistiveTouch", None, "v", "Non"), ("Toucher pour activer", None, "i", 1),
                                         ("Toucher le dos", None, "v", "Non")],
                             (2, prog(t, T_DOS - 0.25, 0.15)) if t < T_DOS + 0.1 else None, "Accessibilité")
        choix = 0 if t < T_LAM else (1 if t < T_APP else 2)
        opts = ecran_reglages("Toucher deux fois", [("Aucune", None, "c", False), ("Capture d'écran", None, "c", t >= T_CAP and choix == 0),
                                                    ("Lampe de poche", None, "c", choix == 1), ("Appareil photo", None, "c", choix == 2),
                                                    ("Centre de contrôle", None, "c", False)], None, "Toucher le dos", "Système")
        dos = ecran_reglages("Toucher le dos", [("Toucher deux fois", None, "v", ["Capture", "Lampe", "Photo"][choix]),
                                                ("Toucher trois fois", None, "v", "Lampe" if t > T_TRI + 0.6 else "Aucune")],
                             (1, 1.0) if T_TRI + 0.2 < t < T_TRI + 0.7 else None, "Toucher")
        if t < T_ACC:
            return reg
        if t < T_TOU:
            return glisse(reg, acc, prog(t, T_ACC, 0.35))
        if t < T_DOS:
            return glisse(acc, tou, prog(t, T_TOU, 0.35))
        if t < T_CHO:
            return glisse(tou, dos, prog(t, T_DOS, 0.35))
        if t < T_TRI:
            return glisse(dos, opts, prog(t, T_CHO, 0.35))
        return glisse(opts, dos, prog(t, T_TRI, 0.35))
    def scene(f, t):
        if t < T_Q:
            # retournement : face -> dos -> face
            if t < T_FLIP1:
                cote, sx = "face", 1
            elif t < T_FLIP2:
                p = prog(t, T_FLIP1, 0.3)
                cote, sx = ("face", 1 - 2 * p) if p < .5 else ("dos", 2 * p - 1)
            else:
                p = prog(t, T_FLIP2, 0.3)
                cote, sx = ("dos", 1 - 2 * p) if p < .5 else ("face", 2 * p - 1)
            if t > T_TRI + 0.8:  # le triple tapotement : on montre le dos et la lampe
                p = prog(t, T_TRI + 0.8, 0.3)
                cote, sx = ("face", 1 - 2 * p) if p < .5 else ("dos", 2 * p - 1)
            if cote == "face":
                if t < T_REG - 0.2:  # écran d'accueil : fond rouge sombre
                    e = Image.new("RGBA", (ECR_W, ECR_H), (40, 8, 12, 255))
                    for k in range(12):
                        x, y = 50 + (k % 4) * 90, 120 + (k // 4) * 110
                        e.alpha_composite(rrect(64, 64, 16, ((200, 40, 50), (240, 240, 245), (90, 90, 96))[k % 3] + (255,)), (x, y))
                    barre_etat(e, (255, 255, 255))
                else:
                    e = ecran_v1(t)
                im = telephone(e)
            else:
                lampe = prog(t, at("deuxième") - 0.1, 0.2) if t > T_TRI else 0
                im = dos_telephone(round(lampe, 1))
            im = im.resize((max(2, int(TEL_W * abs(sx))), TEL_H), Image.BICUBIC)
            f.alpha_composite(im, (int(TEL_CX - im.width / 2), int(TEL_CY - TEL_H / 2)))
            # tapotements au dos
            for k in range(2):
                toucher(f, TEL_CX + 40, TEL_CY + 120, t, at("dos") + 0.2 + k * 0.25)
            for k in range(3):
                toucher(f, TEL_CX + 40, TEL_CY + 120, t, T_TRI + 1.2 + k * 0.22)
            # toucher les lignes
            for tt0, row in ((T_ACC - 0.25, 1), (T_TOU - 0.25, 2), (T_DOS - 0.25, 2)):
                base = 70 + 84 + (44 if row == 2 and tt0 > T_ACC else 0) + (36 if tt0 == T_TOU - 0.25 else 0)
                toucher(f, *ecr(200, base + row * 74 + 37), t, tt0)
            for tt0, row in ((T_CAP, 1), (T_LAM, 2), (T_APP, 3)):
                toucher(f, *ecr(200, 70 + 44 + 84 + 36 + row * 74 + 37), t, tt0 - 0.1)
            # bandeaux
            if t < T_FLIP2:
                bandeau(f, "TON IPHONE A UN BOUTON CACHÉ", t, -0.2, 375, ROUGE, BLANC, 50)
            if T_FLIP1 + 0.3 < t < T_FLIP2:
                bandeau(f, "TAP TAP AU DOS", t, at("dos"), 1180, BLANC, NOIR, 56)
            if T_REG - 0.1 < t < T_CHO:
                bandeau(f, "RÉGLAGES › ACCESSIBILITÉ › TOUCHER", t, T_REG, 375, NOIR, BLANC, 36)
            if T_CHO < t < T_TRI:
                bandeau(f, "1 ACTION AU CHOIX", t, T_CHO, 375, ROUGE, BLANC, 56)
            if t > T_TRI:
                bandeau(f, "×3 = LAMPE DE POCHE", t, T_TRI + 0.8, 375, ROUGE, BLANC, 56)
        else:
            carte_question(f, t, T_Q, [("TU", BLANC), ("CONNAISSAIS ?", ROUGE)], "Oui !", ["OUI", "NON"])
    ZOOMS = [(T_REG, T_CHO, 1.18, TEL_CX, TEL_CY - 120), (T_CHO, T_TRI, 1.25, TEL_CX, TEL_CY - 60)]
    COUPES = [T_FLIP1, T_FLIP2, T_CHO, T_TRI, T_Q]
    TAPS = [at("dos") + 0.2, at("dos") + 0.45, T_ACC - 0.25, T_TOU - 0.25, T_DOS - 0.25, T_CAP - .1, T_LAM - .1, T_APP - .1] + \
           [T_TRI + 1.2 + k * 0.22 for k in range(3)]
    PUNCH = [T_FLIP1 + 0.3, T_TRI + 1.2]
    REPONSE = T_Q + 0.9
elif VIDEO == "2":  # clavier trackpad
    TXT = "Rendez-vous demain à 18h devnt le cinéma"
    POS_FAUTE = TXT.index("devnt") + 3  # entre « dev » et « nt »
    T_APPUI, T_TP, T_PLACE, T_Q = coupe("reste"), at("trackpad") - 0.1, coupe("tu"), coupe("enregistre")
    def ecran_v2(t):
        e = Image.new("RGBA", (ECR_W, ECR_H), (255, 255, 255, 255))
        barre_etat(e)
        d = ImageDraw.Draw(e)
        d.text((28, 70), "Notes", font=police(800, 40), fill=(0, 0, 0))
        corr = t > T_PLACE + 1.6
        txt = TXT.replace("devnt", "devant") if corr else TXT
        f = police(600, 34)
        # retour à la ligne simple
        lignes, l = [], ""
        for mot in txt.split(" "):
            if f.getlength(l + " " + mot) > ECR_W - 70 and l:
                lignes.append(l); l = mot
            else:
                l = (l + " " + mot).strip()
        lignes.append(l)
        for j, l in enumerate(lignes):
            d.text((32, 150 + j * 50), l, font=f, fill=(0, 0, 0))
        # position du curseur : avant l'astuce il saute au mauvais endroit ; en mode trackpad il glisse
        def xy_index(idx):
            n = 0
            for j, l in enumerate(lignes):
                if idx <= n + len(l):
                    return 32 + f.getlength(l[:idx - n]), 150 + j * 50
                n += len(l) + 1
            return 32 + f.getlength(lignes[-1]), 150 + (len(lignes) - 1) * 50
        if t < T_APPUI:
            idx = [len(TXT), 8, 30, 14][min(3, int(t / 0.5))]
        elif t < T_TP:
            idx = len(TXT)
        else:
            p = in_out(prog(t, T_TP + 0.3, max(0.3, T_PLACE + 1.2 - T_TP - 0.3)))
            idx = int(len(TXT) + (POS_FAUTE - len(TXT)) * p)
            if corr:
                idx = POS_FAUTE + 1
        cx_, cy_ = xy_index(idx)
        if math.floor(t * 2.5) % 2 == 0 or t >= T_TP:
            d.rectangle([cx_ - 1, cy_ + 2, cx_ + 3, cy_ + 44], fill=ROUGE)
        # clavier
        y0 = ECR_H - 400
        d.rectangle([0, y0, ECR_W, ECR_H], fill=(208, 211, 217))
        tp = clamp((t - T_TP + 0.2) / 0.3) if T_TP - 0.2 < t < T_Q else 0
        rangs = ["AZERTYUIOP", "QSDFGHJKLM", "WXCVBN"]
        kw, kh = (ECR_W - 24) / 10, 64
        for r, rg in enumerate(rangs):
            off = 12 + (10 - len(rg)) * kw / 2 if r == 2 else 12
            for k, ch in enumerate(rg):
                x = off + k * kw
                y = y0 + 16 + r * (kh + 14)
                col = tuple(int(255 * (1 - tp) + 222 * tp) for _ in range(3))
                d.rounded_rectangle([x + 3, y, x + kw - 3, y + kh], radius=9, fill=col)
                if tp < 0.9:
                    g = police(600, 28)
                    d.text((x + kw / 2 - g.getlength(ch) / 2, y + 14), ch, font=g, fill=(0, 0, 0, int(255 * (1 - tp))))
        ye = y0 + 16 + 3 * (kh + 14)
        d.rounded_rectangle([12 + 3, ye, 12 + kw * 2 - 3, ye + kh], radius=9, fill=(172, 177, 186))
        appui = T_APPUI + 0.3 <= t < T_PLACE + 1.3
        d.rounded_rectangle([12 + kw * 2 + 3, ye, 12 + kw * 8 - 3, ye + kh], radius=9,
                            fill=(170, 170, 176) if appui and tp < 0.5 else tuple(int(255 * (1 - tp) + 222 * tp) for _ in range(3)))
        if tp < 0.9:
            g = police(600, 24)
            d.text((12 + kw * 5 - g.getlength("espace") / 2, ye + 18), "espace", font=g, fill=(0, 0, 0))
        d.rounded_rectangle([12 + kw * 8 + 3, ye, ECR_W - 15, ye + kh], radius=9, fill=(172, 177, 186))
        return e
    def scene(f, t):
        if t < T_Q:
            f.alpha_composite(telephone(ecran_v2(t)), (TEL_CX - TEL_W // 2, TEL_CY - TEL_H // 2))
            if t < T_APPUI:
                for k in range(4):
                    toucher(f, *ecr([300, 180, 120, 260][k], [180, 180, 230, 180][k]), t, k * 0.5 + 0.05)
                if t > 0.9:
                    p = prog(t, 0.9, 0.2)
                    poser(f, texte("X", 260, ROUGE, 900), TEL_CX, TEL_CY - 200, 0.6 + 0.4 * p, p * 0.9)
                bandeau(f, "ARRÊTE DE CORRIGER COMME ÇA", t, -0.2, 375, ROUGE, BLANC, 50)
            else:
                ky = TEL_CY + TEL_H / 2 - INS - 400 + 16 + 3 * 78 + 32
                if t < T_TP + 0.3:
                    toucher(f, TEL_CX, ky, t, T_APPUI + 0.3, long=True)
                    bandeau(f, "APPUI LONG SUR ESPACE", t, T_APPUI, 375, NOIR, BLANC, 50)
                else:  # le doigt glisse sur le clavier devenu trackpad
                    p = in_out(prog(t, T_TP + 0.3, max(0.3, T_PLACE + 1.2 - T_TP - 0.3)))
                    toucher(f, TEL_CX + 120 - 260 * p, ky - 120 * p, t, T_TP + 0.3, long=True) if t < T_PLACE + 1.3 else None
                    bandeau(f, "TON CLAVIER = TRACKPAD", t, T_TP, 375, ROUGE, BLANC, 50)
                if t > T_PLACE + 1.5:
                    bandeau(f, "CURSEUR AU PIXEL PRÈS", t, T_PLACE + 1.5, 1170, BLANC, NOIR, 46)
        else:
            if t < at("team") - 0.1:
                p = ressort(t, T_Q, 2.6, 7)
                poser(f, texte("ENREGISTRE", 130, BLANC), CX, 640, 0.7 + 0.3 * p)
                poser(f, texte("POUR PLUS TARD", 80, ROUGE), CX, 780, 0.7 + 0.3 * p)
                # icône signet
                b = Image.new("RGBA", (160, 200), (0, 0, 0, 0))
                ImageDraw.Draw(b).polygon([(0, 0), (160, 0), (160, 200), (80, 140), (0, 200)], fill=BLANC)
                poser(f, b, CX, 1000, 0.6 + 0.4 * ressort(t, T_Q + 0.2))
            else:
                carte_question(f, t, at("team") - 0.1, [("TEAM CLAVIER", BLANC), ("OU TEAM DICTÉE ?", ROUGE)], "Clavier", ["CLAVIER", "DICTÉE"])
    ZOOMS = [(T_APPUI, T_TP + 0.3, 1.18, TEL_CX, TEL_CY + 80), (T_PLACE, T_Q, 1.3, TEL_CX - 30, TEL_CY - 140)]
    COUPES = [T_APPUI, T_TP, T_PLACE, T_Q, at("team") - 0.1]
    TAPS = [k * 0.5 + 0.05 for k in range(4)] + [T_APPUI + 0.3]
    PUNCH = [0.9, T_TP, T_PLACE + 1.6]
    REPONSE = at("team") + 0.8
elif VIDEO == "3":  # 3 réglages batterie
    T1, T2, T3, T_Q = coupe("un"), coupe("deux"), coupe("trois", 2), coupe("il")
    def batterie(fond, t, cx, cy, niveau, taille=1.0):
        w, h = int(300 * taille), int(150 * taille)
        b = Image.new("RGBA", (w + 30, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(b)
        d.rounded_rectangle([0, 0, w, h], radius=int(30 * taille), outline=BLANC, width=int(10 * taille))
        d.rounded_rectangle([w + 6, h * .32, w + 26, h * .68], radius=6, fill=BLANC)
        col = ROUGE if niveau < 0.25 else (VERT if niveau > 0.6 else (255, 190, 40))
        d.rounded_rectangle([18 * taille, 18 * taille, 18 * taille + (w - 36 * taille) * niveau, h - 18 * taille], radius=int(16 * taille), fill=col)
        poser(fond, b, cx, cy)
        poser(fond, texte(f"{int(niveau * 100)} %", int(70 * taille), BLANC), cx, cy + h * 0.9)
    def ecran_v3(t):
        if t < T2:
            apps = [("Mail", (10, 122, 255)), ("Météo", (90, 170, 250)), ("Jeu", (255, 149, 0)), ("Réseau social", (175, 82, 222)), ("Vidéos", ROUGE)]
            lig = [("Activée via", None, "v", "Wi-Fi")]
            for k, (n, c) in enumerate(apps):
                on = 1.0 if k == 0 else 1 - clamp((t - (at("utiles") - 0.4 + k * 0.18)) / 0.2)
                lig.append((n, c, "i", on))
            return ecran_reglages("Actualisation", lig, None, "Général")
        if t < T3:
            noms = ["Lieux importants", "Suggestions selon le lieu", "Publicités selon le lieu", "Trafic routier", "Localiser"]
            lig = []
            for k, n in enumerate(noms):
                garder = n == "Localiser"
                on = 1.0 if garder else 1 - clamp((t - (at("coupe") - 0.1 + k * 0.15)) / 0.2)
                lig.append((n, None, "i", on))
            return ecran_reglages("Services système", lig, None, "Localisation")
        on = 1 - clamp((t - (at("désactiver") - 0.1)) / 0.25)
        return ecran_reglages("Analyses", [("Partager l'analyse de l'iPhone", None, "i", on), ("Améliorer Siri et Dictée", None, "i", on)],
                              None, "Confidentialité")
    def scene(f, t):
        if t < T1:
            niv = 1 - 0.95 * in_out(prog(t, 0.0, T1))
            batterie(f, t, CX, 760, niv, 1.4)
            bandeau(f, "3 RÉGLAGES QUI VIDENT", t, -0.2, 380, ROUGE, BLANC, 60)
            bandeau(f, "TA BATTERIE POUR RIEN", t, 0.4, 480, BLANC, NOIR, 56)
        elif t < T_Q:
            f.alpha_composite(telephone(ecran_v3(t)), (TEL_CX - TEL_W // 2, TEL_CY - TEL_H // 2))
            if t < T2:
                bandeau(f, "#1 ACTUALISATION EN ARRIÈRE-PLAN", t, T1, 375, ROUGE, BLANC, 38)
            elif t < T3:
                bandeau(f, "#2 SERVICES SYSTÈME", t, T2, 375, ROUGE, BLANC, 50)
            else:
                bandeau(f, "#3 PARTAGE DES ANALYSES", t, T3, 375, ROUGE, BLANC, 46)
                if t > at("désactiver") + 0.3:
                    bandeau(f, "DÉSACTIVÉ", t, at("désactiver") + 0.3, 1170, BLANC, NOIR, 50)
        else:
            if t < at("connais") - 0.4:
                p = ressort(t, T_Q, 2.4, 6)
                poser(f, texte("ET LE #4 ?", 150, BLANC), CX, 700, 0.6 + 0.4 * p)
                poser(f, texte("?", 360, ROUGE), CX, 1000, 0.5 + 0.5 * ressort(t, T_Q + 0.3))
            else:
                carte_question(f, t, at("connais") - 0.4, [("TU CONNAIS", BLANC), ("LE #4 ?", ROUGE)], "Le mode économie !")
    ZOOMS = [(T1 + 0.3, T2, 1.2, TEL_CX, TEL_CY - 100), (T2 + 0.3, T3, 1.2, TEL_CX, TEL_CY - 100), (T3 + 0.3, T_Q, 1.3, TEL_CX, TEL_CY - 160)]
    COUPES = [T1, T2, T3, T_Q]
    TAPS = [at("utiles") - 0.4 + k * 0.18 for k in range(1, 5)] + [at("coupe") - 0.1 + k * 0.15 for k in range(4)] + [at("désactiver") - 0.1]
    PUNCH = [T1, T2, T3, T_Q]
    REPONSE = at("connais") + 0.5
elif VIDEO == "4":  # Texte en direct
    T_CAM, T_ICONE, T_SEL, T_COP, T_COL, T_PLUS, T_Q = (coupe("vise"), at("touche") - 0.05, at("sélectionnes") - 0.05,
                                                       at("copies") - 0.05, at("colles") - 0.05, at("numéro") - 0.35, coupe("dis-moi"))
    CODE = "7HQ2-9KD3-PL4M"
    def etiquette_box():
        k = ("box",)
        if k not in _c:
            im = rrect(330, 200, 18, (250, 250, 248, 255)).copy()
            d = ImageDraw.Draw(im)
            d.text((22, 20), "Réseau : Box-4F2A", font=police(600, 24), fill=(40, 40, 44))
            d.text((22, 70), "Clé Wi-Fi :", font=police(600, 24), fill=(40, 40, 44))
            d.text((22, 112), CODE, font=police(800, 34), fill=(0, 0, 0))
            for x in range(22, 300, 9):  # code-barres
                d.rectangle([x, 168, x + (3 if x % 2 else 5), 190], fill=(0, 0, 0))
            _c[k] = im
        return _c[k]
    def ecran_v4(t):
        if t < T_COL + 0.2:
            e = Image.new("RGBA", (ECR_W, ECR_H), (30, 28, 32, 255))
            g = np.linspace(0, 1, ECR_H)[:, None]
            arr = (np.array([70, 64, 60]) * (1 - g) + np.array([24, 22, 26]) * g).astype(np.uint8)
            e = Image.fromarray(np.dstack([np.repeat(arr[:, None, :], ECR_W, 1), np.full((ECR_H, ECR_W), 255, np.uint8)]), "RGBA")
            box = etiquette_box()
            bx, by = (ECR_W - box.width) // 2, 300
            e.alpha_composite(box, (bx, by))
            d = ImageDraw.Draw(e)
            mode = t >= T_ICONE + 0.1
            if t > T_CAM + 0.6:  # crochets de détection
                c = (255, 214, 10)
                for (x, y, dx, dy) in ((bx - 10, by - 10, 1, 1), (bx + box.width + 10, by - 10, -1, 1),
                                       (bx - 10, by + box.height + 10, 1, -1), (bx + box.width + 10, by + box.height + 10, -1, -1)):
                    d.line([(x, y), (x + 30 * dx, y)], fill=c, width=5)
                    d.line([(x, y), (x, y + 30 * dy)], fill=c, width=5)
            if mode:  # mode texte : fond assombri, texte surligné
                voile = Image.new("RGBA", (ECR_W, ECR_H), (0, 0, 0, 120))
                e.alpha_composite(voile)
                e.alpha_composite(box, (bx, by))
            if t >= T_SEL:
                p = out_cubic(prog(t, T_SEL, 0.4))
                fsel = police(800, 34)
                lw = fsel.getlength(CODE)
                sel = Image.new("RGBA", (int(lw * p) + 6, 46), (10, 122, 255, 90))
                e.alpha_composite(sel, (bx + 19, by + 108))
            if t >= T_SEL + 0.4:  # bulle Copier
                bul = pilule("Copier   Tout sélect.", 24, (40, 40, 44), BLANC, 22, 10, 600)
                e.alpha_composite(bul, (bx + 10, by - 70))
            # bouton déclencheur + icône texte
            d.ellipse([ECR_W / 2 - 50, ECR_H - 190, ECR_W / 2 + 50, ECR_H - 90], outline=BLANC, width=6)
            d.ellipse([ECR_W / 2 - 40, ECR_H - 180, ECR_W / 2 + 40, ECR_H - 100], fill=BLANC)
            if t > T_CAM + 0.6:
                ix, iy = ECR_W - 100, ECR_H - 175
                d.rounded_rectangle([ix, iy, ix + 70, iy + 70], radius=14, fill=(255, 214, 10) if mode else (60, 58, 62))
                for k in range(3):
                    d.rectangle([ix + 16, iy + 18 + k * 13, ix + 54 - (16 if k == 2 else 0), iy + 24 + k * 13], fill=(0, 0, 0) if mode else BLANC)
            barre_etat(e, BLANC)
            return e
        # écran Wi-Fi : on colle
        n_pts = int(clamp((t - T_COL - 0.15) / 0.3) * len(CODE))
        e = ecran_reglages("Box-4F2A", [("Mot de passe", None, "v", "•" * n_pts if n_pts else "")], None, "Wi-Fi")
        d = ImageDraw.Draw(e)
        if t > T_COL + 0.55:
            d.text((40, 360), "Connecté", font=police(800, 34), fill=VERT)
        return e
    def scene(f, t):
        if t < T_CAM:
            poser(f, etiquette_box(), CX, 760, 1.9)
            # crayon barré
            p = out_cubic(prog(t, 0.6, 0.3))
            d = ImageDraw.Draw(f)
            if p > 0:
                d.line([(CX - 330, 600), (CX - 330 + 660 * p, 920)], fill=ROUGE, width=24)
            bandeau(f, "ARRÊTE DE RECOPIER ÇA", t, -0.2, 380, ROUGE, BLANC, 60)
        elif t < T_PLUS:
            f.alpha_composite(telephone(ecran_v4(t)), (TEL_CX - TEL_W // 2, TEL_CY - TEL_H // 2))
            toucher(f, *ecr(ECR_W - 65, ECR_H - 140), t, T_ICONE - 0.1)
            toucher(f, *ecr(ECR_W // 2 - 20, 300 + 130), t, T_SEL - 0.1)
            toucher(f, *ecr(80, 300 - 50), t, T_COP - 0.1)
            if t < T_ICONE:
                bandeau(f, "VISE AVEC L'APPAREIL PHOTO", t, T_CAM, 375, NOIR, BLANC, 46)
            elif t < T_SEL:
                bandeau(f, "TOUCHE L'ICÔNE TEXTE", t, T_ICONE, 375, ROUGE, BLANC, 50)
            elif t < coupe("ça"):
                bandeau(f, "SÉLECTIONNE · COPIE · COLLE", t, T_SEL, 375, ROUGE, BLANC, 44)
            else:
                bandeau(f, "ÇA MARCHE AUSSI SUR", t, coupe("ça"), 380, BLANC, NOIR, 54)
        else:
            if t < T_Q:
                bandeau(f, "ÇA MARCHE AUSSI SUR", t, T_PLUS, 380, BLANC, NOIR, 54)
                for k, (lib, mot) in enumerate((("UN NUMÉRO", "numéro"), ("UNE ADRESSE", "adresse"), ("UN MENU", "menu"))):
                    t0 = at(mot) - 0.1
                    if t >= t0:
                        c = rrect(700, 150, 40, (30, 28, 32, 245), (255, 255, 255, 40), 2).copy()
                        c.alpha_composite(texte(lib, 64, BLANC, 900, 560), (60, 40))
                        ImageDraw.Draw(c).ellipse([590, 45, 650, 105], fill=ROUGE)
                        poser(f, c, CX + (1 - out_expo(prog(t, t0, 0.4))) * 600, 620 + k * 190)
            else:
                carte_question(f, t, T_Q, [("TU SCANNES QUOI", BLANC), ("EN PREMIER ?", ROUGE)], "Le menu du resto")
    ZOOMS = [(T_ICONE - 0.2, T_COL, 1.35, TEL_CX, TEL_CY - 80)]
    COUPES = [T_CAM, T_COL, T_PLUS, T_Q]
    TAPS = [T_ICONE - 0.1, T_SEL - 0.1, T_COP - 0.1]
    PUNCH = [0.6, T_ICONE, T_COL + 0.55]
    REPONSE = T_Q + 0.9
else:  # avis tranché
    T_AVIS, T_ANS, T_BAT, T_DIFF, T_Q = coupe("mon"), coupe("garde-le"), at("batterie") - 0.1, at("différence") - 0.2, coupe("et", 2)
    def mini_tel(f, couleur, label, cx, cy, ech, rot=0):
        e = Image.new("RGBA", (ECR_W, ECR_H), couleur + (255,))
        barre_etat(e, BLANC)
        poser(f, telephone(e), cx, cy, ech, 1, rot)
        poser(f, pilule(label, 40, BLANC, NOIR, 26, 10), cx, cy + TEL_H * ech / 2 + 50)
    def scene(f, t):
        if t < T_AVIS:
            mini_tel(f, (60, 60, 70), "L'AN DERNIER", CX - 200, 820, 0.55, 4)
            mini_tel(f, (150, 20, 30), "LE NOUVEAU", CX + 200, 820, 0.55, -4)
            bandeau(f, "CHANGER D'IPHONE", t, -0.2, 375, ROUGE, BLANC, 60)
            bandeau(f, "CHAQUE ANNÉE ?", t, 0.3, 485, BLANC, NOIR, 60)
        elif t < T_ANS:
            p = ressort(t, T_AVIS, 2.6, 7)
            poser(f, texte("MON AVIS :", 120, BLANC), CX, 640, 0.7 + 0.3 * p)
            if t >= at("rien") - 0.1:
                poser(f, pilule("À RIEN", 150, ROUGE, BLANC, 60, 20), CX, 880, 0.5 + 0.5 * ressort(t, at("rien") - 0.1), 1, -5)
        elif t < T_Q:
            ans = 1 + clamp((t - T_ANS) / 1.0) * 2
            poser(f, texte(f"{ans:.0f} ANS" if t < T_ANS + 1.0 else "2 À 3 ANS", 150, BLANC), CX, 520, 0.9 + 0.1 * ressort(t, T_ANS))
            if t >= T_BAT:  # batterie neuve
                p = out_cubic(prog(t, T_BAT, 0.6))
                w, h = 360, 170
                b = Image.new("RGBA", (w + 34, h), (0, 0, 0, 0))
                d = ImageDraw.Draw(b)
                d.rounded_rectangle([0, 0, w, h], radius=34, outline=BLANC, width=12)
                d.rounded_rectangle([w + 8, h * .32, w + 30, h * .68], radius=6, fill=BLANC)
                d.rounded_rectangle([20, 20, 20 + (w - 40) * (0.2 + 0.8 * p), h - 20], radius=18, fill=VERT if p > 0.6 else ROUGE)
                poser(f, b, CX, 780)
                poser(f, texte("BATTERIE NEUVE", 64, VERT if p > 0.6 else BLANC), CX, 920)
            if t >= T_DIFF:
                poser(f, pilule("À PEINE LA DIFFÉRENCE", 56, BLANC, NOIR, 34, 14), CX, 1100,
                      0.6 + 0.4 * ressort(t, T_DIFF))
        else:
            carte_question(f, t, T_Q, [("TU LE GARDES", BLANC), ("COMBIEN DE TEMPS ?", ROUGE)], "3 ans minimum", ["1 AN", "2 ANS", "3 ANS +"])
    ZOOMS = []
    COUPES = [T_AVIS, T_ANS, T_Q]
    TAPS = []
    PUNCH = [at("rien") - 0.1, T_BAT + 0.6, T_DIFF]
    REPONSE = T_Q + 0.9

# ---------- image ----------
def zoom_actuel(t):
    z, fx, fy = 1.0, W / 2, H / 2
    for (a, b, zz, x, y) in ZOOMS:
        if a <= t < b:
            p = in_out(prog(t, a, 0.5)) * (1 - in_out(prog(t, b - 0.4, 0.4)))
            z = 1 + (zz - 1) * p
            fx, fy = W / 2 + (x - W / 2) * p, H / 2 + (y - H / 2) * p
    return z, fx, fy

def image(t):
    img = decor(t)
    scene_l = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dessus = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    DESSUS[0] = dessus
    scene(scene_l, t)  # téléphone et contenu (zoomables) ; les bandeaux vont sur « dessus »
    z, fx, fy = zoom_actuel(t)
    if z > 1.001:
        cw, ch = W / z, H / z
        x0, y0 = clamp(fx - cw / 2, 0, W - cw), clamp(fy - ch / 2, 0, H - ch)
        scene_l = scene_l.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.BICUBIC)
    img.alpha_composite(scene_l)
    img.alpha_composite(dessus)
    pp = os.path.join(POLICES, "poppins-latin-800-normal.woff")
    tag_mobile(img, t, pp, None)
    signature(img, t, pp, REPONSE + 0.4, y=1460 - 40)
    sous_titres(img, t)
    for pt in PUNCH:
        x = t - pt
        if 0 <= x < 0.2:
            img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(60 * (1 - x / 0.2)))))
            break
    return img.convert("RGB")

if "--timeline" in sys.argv:
    json.dump({"coupes": COUPES, "punchs": PUNCH, "coches": TAPS, "entrees": [], "rappel": COUPES[-1],
               "cta": COUPES[-1], "go": REPONSE - 0.4, "acc": REPONSE, "duree": DUREE},
              open(sys.argv[sys.argv.index("--timeline") + 1], "w"), indent=1)
    sys.exit()
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
