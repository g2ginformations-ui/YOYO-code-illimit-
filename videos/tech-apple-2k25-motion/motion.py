"""Tech Apple 2K25 — 3 vidéos en motion design (noir et rouge), 1080x1920, 60 i/s, calées sur la voix.

Usage : python3 motion.py <voix.wav> <dossier_polices> <sortie.mp4> --video 1|2|3 [--stills t1,t2,...]
  1 « rapide »        : typographie animée, l'iPhone d'abord.
  2 « éligibilité »   : une interface qui vérifie si tu es éligible.
  3 « compte à rebours » : 3, 2, 1.
Les instants des mots viennent de mots_<video>.json. Le son vient de out/mix.wav (synth_motion.py).
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

W, H, FPS = 1080, 1920, 60
CX = 520  # axe central de la zone sûre TikTok (x 120 à 920, y 280 à 1440)
NOIR, ROUGE, ROUGE_F, BLANC, GRIS = (8, 7, 9), (232, 38, 43), (120, 14, 18), (244, 241, 236), (150, 146, 150)
CARTE_FOND = (22, 20, 24)
FIN_HOLD = 1.6  # secondes tenues sur le CTA après la voix

with wave.open(VOIX) as wf:
    FIN_VOIX = wf.getnframes() / wf.getframerate()
DUREE = FIN_VOIX + FIN_HOLD
NF = int(round(DUREE * FPS))

MOTS = [{"t": w["text"], "s": w["start"], "e": w["end"]}
        for w in json.load(open(os.path.join(ICI, f"mots_{VIDEO}.json")))["words"] if w["type"] == "word"]
def at(txt, n=1):
    """Instant du n-ième mot qui commence par txt (sans tenir compte de la ponctuation)."""
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
def out_expo(p):
    return 1.0 if p >= 1 else 1 - 2 ** (-10 * p)
def in_cubic(p):
    return p ** 3
def ressort(t, t0, freq=3.2, amort=7.0):
    """0 -> 1 avec un rebond d'inertie (dépasse un peu puis se pose)."""
    x = t - t0
    if x <= 0:
        return 0.0
    return 1 - math.exp(-amort * x) * math.cos(2 * math.pi * freq * x)

# ---------- polices et textes ----------
_f = {}
def police(poids, taille):
    k = (poids, taille)
    if k not in _f:
        _f[k] = ImageFont.truetype(os.path.join(POLICES, f"poppins-latin-{poids}-normal.woff"), taille)
    return _f[k]

_tc = {}
def texte(txt, taille, col=BLANC, poids=900, max_l=800):
    """Texte rendu une fois (rétréci si plus large que max_l)."""
    k = (txt, taille, col, poids, max_l)
    if k not in _tc:
        f = police(poids, taille)
        while f.getlength(txt) > max_l and taille > 20:
            taille -= 2
            f = police(poids, taille)
        bb = f.getbbox(txt)
        im = Image.new("RGBA", (bb[2] - bb[0] + 8, bb[3] - bb[1] + 8), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((4 - bb[0], 4 - bb[1]), txt, font=f, fill=col)
        _tc[k] = im
    return _tc[k]

_gc = {}
def lueur(im, rayon=24, force=1.6):
    """Halo flou de la même forme (pour les mots et objets qui brillent)."""
    k = (id(im), rayon)
    if k not in _gc:
        pad = rayon * 3
        g = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
        g.alpha_composite(im, (pad, pad))
        g = g.filter(ImageFilter.GaussianBlur(rayon))
        a = np.array(g)
        a[..., 3] = np.clip(a[..., 3].astype(np.float32) * force, 0, 255).astype(np.uint8)
        _gc[k] = (Image.fromarray(a), pad)
    return _gc[k]

_rc = {}
def rrect(w, h, r, fill, contour=None, ep=0):
    """Rectangle arrondi lissé (dessiné x2 puis réduit)."""
    w, h, r = int(w), int(h), int(r)
    k = (w, h, r, fill, contour, ep)
    if k not in _rc:
        im = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
        ImageDraw.Draw(im).rounded_rectangle([0, 0, w * 2 - 1, h * 2 - 1], radius=r * 2, fill=fill,
                                             outline=contour, width=ep * 2)
        _rc[k] = im.resize((w, h), Image.LANCZOS)
        if len(_rc) > 400:
            _rc.clear()
    return _rc[k]

def poser(fond, im, cx, cy, ech=1.0, alpha=1.0, rot=0.0, flou=0.0):
    """Colle im centré en (cx, cy), avec échelle, opacité, rotation et flou."""
    if im is None or alpha <= 0.01 or ech <= 0.01:
        return
    if abs(ech - 1) > 0.005:
        im = im.resize((max(1, int(im.width * ech)), max(1, int(im.height * ech))), Image.BICUBIC)
    if abs(rot) > 0.2:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    if flou > 0.5:
        im = im.filter(ImageFilter.GaussianBlur(flou))
    if alpha < 0.99:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    fond.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def mot_entre(fond, txt, taille, cx, cy, t, t0, col=BLANC, poids=900, brille=False, d=0.45):
    """Entrée d'un mot : monte de 60 px, se défloute, rebondit légèrement."""
    if t < t0:
        return
    p = out_expo(prog(t, t0, d))
    im = texte(txt, taille, col, poids)
    if brille:
        g, pad = lueur(im, 26)
        poser(fond, g, cx, cy + (1 - p) * 60, 0.96 + 0.04 * ressort(t, t0), p * 0.9)
    poser(fond, im, cx, cy + (1 - p) * 60, 0.96 + 0.04 * ressort(t, t0), p, flou=(1 - p) * 10)

def pilule(txt, taille, fond_col, txt_col, pad_x=44, pad_y=22, poids=900):
    t_im = texte(txt, taille, txt_col, poids, 760 - 2 * pad_x)  # la pilule tient dans les 760 px
    w, h = t_im.width + 2 * pad_x, t_im.height + 2 * pad_y
    im = rrect(w, h, h // 2, fond_col).copy()
    im.alpha_composite(t_im, (pad_x, pad_y))
    return im

def coche(taille, p, fond_col=ROUGE):
    """Rond plein + coche blanche tracée selon p (0 -> 1)."""
    s = 3
    im = Image.new("RGBA", (taille * s, taille * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, taille * s - 1, taille * s - 1], fill=fond_col)
    pts = [(0.28, 0.52), (0.44, 0.68), (0.74, 0.36)]
    pts = [(x * taille * s, y * taille * s) for x, y in pts]
    l1 = math.dist(pts[0], pts[1]); l2 = math.dist(pts[1], pts[2])
    reste = p * (l1 + l2)
    seg = [pts[0]]
    if reste <= l1:
        u = reste / l1
        seg.append((pts[0][0] + (pts[1][0] - pts[0][0]) * u, pts[0][1] + (pts[1][1] - pts[0][1]) * u))
    else:
        u = (reste - l1) / l2
        seg += [pts[1], (pts[1][0] + (pts[2][0] - pts[1][0]) * u, pts[1][1] + (pts[2][1] - pts[1][1]) * u)]
    if p > 0:
        d.line(seg, fill=BLANC, width=int(taille * s * 0.1), joint="curve")
    return im.resize((taille, taille), Image.LANCZOS)

def eclats(fond, t, t0, cx, cy, n=26, portee=340, graine=1):
    """Éclat de particules (rondes et petits traits) qui partent et s'éteignent."""
    x = t - t0
    if not (0 <= x < 0.9):
        return
    rng = np.random.default_rng(graine)
    d = ImageDraw.Draw(fond)
    p = out_cubic(x / 0.9)
    for j in range(n):
        ang = rng.uniform(0, 2 * math.pi)
        dist = portee * rng.uniform(0.4, 1.0) * p
        r = rng.uniform(5, 13) * (1 - p)
        px_, py_ = cx + math.cos(ang) * dist, cy + math.sin(ang) * dist
        col = (ROUGE if j % 3 else BLANC) + (int(255 * (1 - p)),)
        d.ellipse([px_ - r, py_ - r, px_ + r, py_ + r], fill=col)

# ---------- téléphone dessiné (générique, sans logo) ----------
def telephone(larg=360):
    k = ("tel", larg)
    if k in _tc:
        return _tc[k]
    s = 2
    w, h = larg * s, int(larg * 2.06) * s
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=int(w * 0.19), fill=(36, 34, 38))
    d.rounded_rectangle([6, 6, w - 7, h - 7], radius=int(w * 0.18), fill=(14, 13, 15))
    # écran : dégradé rouge vers noir + deux ronds doux
    ins = int(w * 0.045)
    ecran = Image.new("RGBA", (w - 2 * ins, h - 2 * ins), (0, 0, 0, 0))
    g = np.linspace(0, 1, ecran.height)[:, None]
    top, bas = np.array([232, 38, 43]), np.array([40, 6, 9])
    arr = (top * (1 - g) ** 1.4 + bas * (1 - (1 - g) ** 1.4)).astype(np.uint8)
    arr = np.repeat(arr[:, None, :], ecran.width, axis=1)
    grad = Image.fromarray(np.dstack([arr.reshape(ecran.height, ecran.width, 3),
                                      np.full((ecran.height, ecran.width), 255, np.uint8)]), "RGBA")
    masque = Image.new("L", ecran.size, 0)
    ImageDraw.Draw(masque).rounded_rectangle([0, 0, ecran.width - 1, ecran.height - 1], radius=int(w * 0.15), fill=255)
    ecran.paste(grad, (0, 0), masque)
    rond = Image.new("RGBA", ecran.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(rond)
    dr.ellipse([-ecran.width * 0.3, ecran.height * 0.45, ecran.width * 0.8, ecran.height * 1.05], fill=(255, 120, 120, 60))
    dr.ellipse([ecran.width * 0.35, ecran.height * 0.1, ecran.width * 1.3, ecran.height * 0.6], fill=(255, 255, 255, 30))
    rond = rond.filter(ImageFilter.GaussianBlur(40))
    rond.putalpha(Image.fromarray(np.minimum(np.array(rond.getchannel("A")), np.array(masque))))
    ecran.alpha_composite(rond)
    im.alpha_composite(ecran, (ins, ins))
    # îlot en haut + boutons latéraux
    d.rounded_rectangle([w * 0.36, ins + w * 0.04, w * 0.64, ins + w * 0.115], radius=int(w * 0.04), fill=(0, 0, 0))
    d.rounded_rectangle([w - 4, h * 0.22, w + 2, h * 0.32], radius=4, fill=(60, 58, 62))
    d.rounded_rectangle([-2, h * 0.2, 4, h * 0.26], radius=4, fill=(60, 58, 62))
    d.rounded_rectangle([-2, h * 0.28, 4, h * 0.38], radius=4, fill=(60, 58, 62))
    im = im.resize((w // s, h // s), Image.LANCZOS)
    _tc[k] = im
    return im

def icone_pc(larg=150):
    k = ("pc", larg)
    if k not in _tc:
        s = 3
        w, h = larg * s, int(larg * 0.9) * s
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, w - 1, h * 0.68], radius=int(w * 0.06), fill=BLANC)
        d.rounded_rectangle([w * 0.05, h * 0.06, w * 0.95, h * 0.6], radius=int(w * 0.03), fill=ROUGE)
        d.rectangle([w * 0.44, h * 0.68, w * 0.56, h * 0.86], fill=BLANC)
        d.rounded_rectangle([w * 0.28, h * 0.86, w * 0.72, h - 1], radius=int(w * 0.03), fill=BLANC)
        _tc[k] = im.resize((w // s, h // s), Image.LANCZOS)
    return _tc[k]

# ---------- décor ----------
def _halo(r, col, a):
    y, x = np.mgrid[-r:r, -r:r].astype(np.float32)
    d = np.sqrt(x * x + y * y) / r
    al = np.clip(1 - d, 0, 1) ** 2.2 * a
    return Image.fromarray(np.dstack([np.full_like(al, col[0]), np.full_like(al, col[1]), np.full_like(al, col[2]),
                                      al]).astype(np.uint8), "RGBA")
HALO1 = _halo(900, (200, 20, 26), 150)
HALO2 = _halo(600, (120, 10, 40), 110)
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_vig = np.clip(((_xx - W / 2) / (W * 0.75)) ** 2 + ((_yy - H / 2) / (H * 0.7)) ** 2, 0, 1)
VIGNETTE = Image.fromarray(np.dstack([np.zeros((H, W, 3), np.uint8), (_vig * 200).astype(np.uint8)]), "RGBA")
_rng = np.random.default_rng(3)
GRAINS = [Image.fromarray(np.dstack([np.full((H // 2, W // 2, 3), 255, np.uint8),
                                     (_rng.random((H // 2, W // 2)) * 14).astype(np.uint8)]), "RGBA").resize((W, H))
          for _ in range(3)]

def decor(t):
    img = Image.new("RGBA", (W, H), NOIR + (255,))
    img.alpha_composite(HALO1, (int(W / 2 - 900 + math.sin(t * 0.5) * 120), int(H * 0.42 - 900 + math.cos(t * 0.4) * 160)))
    img.alpha_composite(HALO2, (int(W * 0.8 - 600 + math.cos(t * 0.6) * 140), int(H * 0.75 - 600 + math.sin(t * 0.5) * 120)))
    # anneau fin qui tourne lentement au centre
    d = ImageDraw.Draw(img)
    r = 430 + math.sin(t * 0.8) * 20
    a0 = (t * 30) % 360
    d.arc([CX - r, 760 - r, CX + r, 760 + r], a0, a0 + 250, fill=(255, 255, 255, 18), width=2)
    img.alpha_composite(VIGNETTE)
    img.alpha_composite(GRAINS[int(t * 24) % 3])
    return img

# ---------- briques communes ----------
def s_iphone(fond, t, t_app, t_gratuit, titre_y=420):
    """L'iPhone 18 Pro qui arrive en rebond, puis la pilule GRATUIT."""
    mot_entre(fond, "IPHONE 18 PRO", 92, CX, titre_y, t, t_app - 0.1)
    if t >= t_app:
        p = ressort(t, t_app, 2.4, 6)
        tel = telephone(290)
        g, pad = lueur(tel, 40, 1.2)
        fl = math.sin(t * 2.2) * 10
        rot = (1 - out_cubic(prog(t, t_app, 0.7))) * -18 + math.sin(t * 1.6) * 2.5
        poser(fond, g, CX, 780 + fl, 0.6 + 0.4 * p, min(1, (t - t_app) * 4) * 0.8, rot)
        poser(fond, tel, CX, 780 + fl, 0.6 + 0.4 * p, min(1, (t - t_app) * 4), rot)
    if t >= t_gratuit:
        p = ressort(t, t_gratuit, 3, 8)
        pl = pilule("GRATUIT", 84, ROUGE, BLANC)
        g, pad = lueur(pl, 30)
        poser(fond, g, CX, 1050, 0.4 + 0.6 * p, 0.9, -4)
        poser(fond, pl, CX, 1050, 0.4 + 0.6 * p, 1, -4)
        eclats(fond, t, t_gratuit, CX, 1050, graine=7)

def s_tech(fond, t, t0, t_2k25, haut="GRÂCE À LA"):
    mot_entre(fond, haut, 54, CX, 470, t, t0, GRIS, 600)
    mot_entre(fond, "TECH APPLE", 120, CX, 600, t, t0 + 0.12)
    if t >= t_2k25 - 0.05:
        p = ressort(t, t_2k25 - 0.05, 2.6, 6)
        im = texte("2K25", 250, ROUGE)
        g, pad = lueur(im, 40, 1.4)
        poser(fond, g, CX, 820, 0.5 + 0.5 * p, 0.8)
        poser(fond, im, CX, 820, 0.5 + 0.5 * p, min(1, (t - t_2k25 + 0.05) * 5))
        eclats(fond, t, t_2k25, CX, 820, 30, 420, 3)

def carte_condition(fond, t, t0, t_ok, cy, icone, titre, sous):
    """Carte qui glisse depuis la droite, puis se coche."""
    if t < t0:
        return
    p = out_expo(prog(t, t0, 0.55))
    c = rrect(800, 200, 44, CARTE_FOND + (235,), (255, 255, 255, 30), 2).copy()
    poser(c, icone, 110, 100)
    c.alpha_composite(texte(titre, 54, BLANC, 800, 460), (200, 46))
    c.alpha_composite(texte(sous, 34, GRIS, 600, 460), (202, 116))
    if t >= t_ok:
        poser(c, coche(96, out_cubic(prog(t, t_ok, 0.35))), 720, 100, 0.7 + 0.3 * ressort(t, t_ok))
    poser(fond, c, CX + (1 - p) * 700, cy, 1, p)

def rond_icone(txt):
    k = ("rond", txt)
    if k not in _tc:
        im = rrect(130, 130, 65, (40, 14, 16, 255), ROUGE + (255,), 4).copy()
        poser(im, texte(txt, 46, BLANC, 900), 65, 65)
        _tc[k] = im
    return _tc[k]

def icone_duo():
    k = ("duo",)
    if k not in _tc:
        im = rrect(130, 130, 65, (40, 14, 16, 255), ROUGE + (255,), 4).copy()
        poser(im, icone_pc(64), 50, 66)
        poser(im, telephone(30), 92, 70)
        _tc[k] = im
    return _tc[k]

def s_cta(fond, t, t0, t_go, t_acc):
    """CTA : COMMENTE + GO qui rebondit + bulle de commentaire qui s'écrit + je t'accompagne."""
    mot_entre(fond, "COMMENTE", 130, CX, 430, t, t0)
    if t >= t_go - 0.06:
        p = ressort(t, t_go - 0.06, 2.8, 6)
        pouls = 1 + 0.04 * math.sin((t - t_go) * 7) if t > t_go + 0.6 else 1
        pl = pilule("GO", 150, ROUGE, BLANC, 90, 26)
        g, pad = lueur(pl, 40, 1.5)
        poser(fond, g, CX, 640, (0.3 + 0.7 * p) * pouls, 0.9)
        poser(fond, pl, CX, 640, (0.3 + 0.7 * p) * pouls, 1)
        eclats(fond, t, t_go, CX, 640, 30, 380, 11)
    # bulle de commentaire (avatar + champ + flèche d'envoi)
    if t >= t0 + 0.25:
        p = out_expo(prog(t, t0 + 0.25, 0.5))
        b = rrect(800, 150, 75, (30, 28, 32, 245), (255, 255, 255, 40), 2).copy()
        db = ImageDraw.Draw(b)
        db.ellipse([28, 30, 118, 120], fill=ROUGE_F)
        b.alpha_composite(texte("Ajoute un commentaire...", 34, GRIS, 600), (146, 56)) if t < t_go + 0.2 else None
        if t >= t_go + 0.2:
            n = min(2, int((t - t_go - 0.2) / 0.1) + 1)
            b.alpha_composite(texte("GO"[:n], 56, BLANC, 900), (146, 42))
        if math.floor(t * 2.5) % 2 == 0 and t >= t_go + 0.2:
            x = 146 + texte("GO", 56, BLANC, 900).width + 6
            db.rectangle([x, 46, x + 5, 106], fill=ROUGE)
        envoi = ROUGE if t >= t_go + 0.5 else (70, 66, 72)
        db.ellipse([690, 35, 770, 115], fill=envoi)
        db.polygon([(712, 75), (750, 56), (738, 94)], fill=BLANC)
        poser(fond, b, CX, 870 + (1 - p) * 80, 1, p)
    if t >= t_acc - 0.08:
        p = ressort(t, t_acc - 0.08, 2.6, 7)
        pl = pilule("JE T'ACCOMPAGNE GRATUITEMENT", 46, BLANC, NOIR, 40, 22)
        poser(fond, pl, CX, 1060, 0.6 + 0.4 * p, min(1, (t - t_acc + 0.08) * 5))

# ---------- les 3 vidéos ----------
def coupe(mot, n=1):
    return at(mot, n) - 0.15

if VIDEO == "1":  # « rapide »
    C2, C3, C4 = coupe("grâce"), coupe("il"), coupe("c'est")
    T_CTA = coupe("commente")
    def v1_s1(f, t):
        s_iphone(f, t, -0.25, at("gratuit") - 0.06)
    def v1_s2(f, t):
        s_tech(f, t, C2 + 0.05, at("2k25"))
    def v1_s3(f, t):
        mot_entre(f, "IL TE FAUT", 64, CX, 420, t, C3 + 0.05, GRIS, 800)
        mot_entre(f, "2 CHOSES", 130, CX, 540, t, at("deux") - 0.08, BLANC, 900, True)
        carte_condition(f, t, at("être") - 0.1, at("majeur") + 0.25, 790, rond_icone("18+"), "Être majeur", "La seule condition d'âge")
        carte_condition(f, t, at("avoir") - 0.1, at("iphone", 2) + 0.25, 1020, icone_duo(), "Un PC ou un iPhone", "Celui sur lequel tu me regardes")
    def v1_s4(f, t):
        p = ressort(t, C4, 2.6, 6)
        im = texte("C'EST TOUT.", 170, BLANC)
        poser(f, im, CX, 760, 1.15 - 0.15 * p, min(1, (t - C4) * 6))
    SCENES = [(0, v1_s1), (C2, v1_s2), (C3, v1_s3), (C4, v1_s4), (T_CTA, None)]
    PUNCH = [at("gratuit") - 0.06, at("2k25"), at("majeur") + 0.25, at("iphone", 2) + 0.25, C4, at("go") - 0.06]
    CHECKS = [at("majeur") + 0.25, at("iphone", 2) + 0.25]
    ENTREES = [at("être") - 0.1, at("avoir") - 0.1]
    RAPPEL = C3
elif VIDEO == "2":  # « éligibilité »
    C2, C3, C4 = coupe("tu", 2), coupe("félicitations"), coupe("l'iphone")  # le 1er « tu » est dans le hook
    T_CTA = coupe("commente")
    def v2_s1(f, t):
        mot_entre(f, "ES-TU ÉLIGIBLE ?", 100, CX, 420, t, -0.2, BLANC, 900, True)
        if t >= 0.25:
            p = out_expo(prog(t, 0.25, 0.5))
            c = rrect(800, 330, 50, CARTE_FOND + (240,), (255, 255, 255, 30), 2).copy()
            c.alpha_composite(texte("TECH APPLE 2K25", 64, BLANC, 900), (50, 50))
            c.alpha_composite(texte("Vérification en cours...", 36, GRIS, 600), (52, 140))
            barre = rrect(700, 26, 13, (50, 46, 52, 255))
            c.alpha_composite(barre, (50, 240))
            rempl = clamp((t - 0.6) / (C2 - 0.6))
            if rempl > 0.02:
                c.alpha_composite(rrect(max(26, 700 * out_cubic(rempl)), 26, 13, ROUGE + (255,)), (50, 240))
            poser(f, c, CX, 780 + (1 - p) * 80, 1, p)
    def v2_s2(f, t):
        mot_entre(f, "ÉLIGIBILITÉ", 90, CX, 400, t, C2 + 0.03, BLANC, 900)
        ok = (at("majeur") + 0.25, at("iphone") + 0.3)
        n_ok = sum(t >= o for o in ok)
        # anneau de progression autour du pourcentage
        cible = n_ok * 50
        p = out_cubic(prog(t, max([C2] + [o for o in ok if t >= o]), 0.5))
        val = (n_ok - 1) * 50 + 50 * p if n_ok else 0
        r = 120
        anneau = Image.new("RGBA", (r * 6, r * 6), (0, 0, 0, 0))
        da = ImageDraw.Draw(anneau)
        da.ellipse([12, 12, r * 6 - 12, r * 6 - 12], outline=(60, 56, 62), width=36)
        if val > 0:
            da.arc([12, 12, r * 6 - 12, r * 6 - 12], -90, -90 + 360 * val / 100, fill=ROUGE, width=36)
        anneau = anneau.resize((r * 2, r * 2), Image.LANCZOS)
        poser(anneau, texte(f"{int(round(val))}%", 64, BLANC, 900), r, r)
        poser(f, anneau, CX, 590, 0.8 + 0.2 * ressort(t, C2 + 0.05), min(1, (t - C2) * 5))
        carte_condition(f, t, at("majeur") - 0.25, ok[0], 820, rond_icone("18+"), "T'es majeur ?", "Oui")
        carte_condition(f, t, at("pc") - 0.3, ok[1], 1030, icone_duo(), "Un PC ou un iPhone ?", "Oui")
    def v2_s3(f, t):
        t0 = C3
        p = ressort(t, t0, 2.2, 6)
        e = max(0.05, 0.2 + 0.8 * p)
        g, pad = lueur(rrect(440, 440, 220, ROUGE + (255,)), 50, 1.3)
        poser(f, g, CX, 660, e, 0.7)
        poser(f, rrect(440, 440, 220, ROUGE + (255,)), CX, 660, e)
        poser(f, coche(260, out_cubic(prog(t, t0 + 0.2, 0.4)), (0, 0, 0, 0)), CX, 660, e)
        eclats(f, t, t0 + 0.15, CX, 660, 40, 480, 5)
        mot_entre(f, "FÉLICITATIONS", 80, CX, 380, t, at("félicitations") - 0.05, GRIS, 800)
        mot_entre(f, "ÉLIGIBLE", 150, CX, 1000, t, at("éligible", 2) - 0.08, BLANC, 900, True)
    def v2_s4(f, t):
        s_iphone(f, t, C4 + 0.05, at("gratuit") - 0.06)
    SCENES = [(0, v2_s1), (C2, v2_s2), (C3, v2_s3), (C4, v2_s4), (T_CTA, None)]
    PUNCH = [at("majeur") + 0.25, at("iphone") + 0.3, C3, at("gratuit") - 0.06, at("go") - 0.06]
    CHECKS = [at("majeur") + 0.25, at("iphone") + 0.3]
    ENTREES = [at("majeur") - 0.25, at("pc") - 0.3]
    RAPPEL = C3
else:  # « compte à rebours »
    C2, C3, C4 = coupe("trois", 2), coupe("deux"), coupe("un", 3)
    T_CTA = coupe("commente")
    def compte(f, t, t0, chiffre, duree):
        """Gros chiffre + anneau qui se vide pendant `duree`."""
        p = ressort(t, t0, 2.6, 6)
        im = texte(chiffre, 420, BLANC)
        g, pad = lueur(im, 40, 1.0)
        poser(f, g, CX, 640, 1.5 - 0.5 * p, 0.6)
        poser(f, im, CX, 640, 1.5 - 0.5 * p, min(1, (t - t0) * 6))
        r = 300
        an = Image.new("RGBA", (r * 4, r * 4), (0, 0, 0, 0))
        da = ImageDraw.Draw(an)
        reste = 1 - clamp((t - t0) / duree)
        da.arc([10, 10, r * 4 - 10, r * 4 - 10], -90, -90 + 360 * reste, fill=ROUGE, width=18)
        poser(f, an.resize((r * 2, r * 2), Image.LANCZOS), CX, 640, 1, min(1, (t - t0) * 4))
    def v3_s1(f, t):
        mot_entre(f, "DANS 3 SECONDES", 96, CX, 430, t, -0.2, BLANC, 900, True)
        mot_entre(f, "TU SAIS SI", 60, CX, 620, t, at("tu") - 0.08, GRIS, 800)
        mot_entre(f, "TECH APPLE 2K25", 100, CX, 740, t, at("tech") - 0.08, ROUGE, 900, True)
        mot_entre(f, "EST FAITE POUR TOI", 70, CX, 860, t, at("faite") - 0.08, BLANC, 800)
    def v3_s2(f, t):
        compte(f, t, C2 + 0.05, "3", C3 - C2)
        carte_condition(f, t, at("t'es") - 0.15, at("majeur") + 0.25, 1010, rond_icone("18+"), "T'es majeur", "Validé")
    def v3_s3(f, t):
        compte(f, t, C3 + 0.05, "2", C4 - C3)
        carte_condition(f, t, at("t'as") - 0.15, at("iphone") + 0.3, 1010, icone_duo(), "Un PC ou un iPhone", "Validé")
    def v3_s4(f, t):
        if t < at("l'iphone") - 0.15:
            compte(f, t, C4 + 0.05, "1", at("l'iphone") - C4)
        else:
            s_iphone(f, t, at("l'iphone") - 0.1, at("gratuit") - 0.06)
    SCENES = [(0, v3_s1), (C2, v3_s2), (C3, v3_s3), (C4, v3_s4), (T_CTA, None)]
    PUNCH = [C2 + 0.05, C3 + 0.05, C4 + 0.05, at("l'iphone") - 0.1, at("gratuit") - 0.06, at("go") - 0.06]
    CHECKS = [at("majeur") + 0.25, at("iphone") + 0.3]
    ENTREES = [at("t'es") - 0.15, at("t'as") - 0.15]
    RAPPEL = C3

T_GO = at("go") - 0.06
T_ACC = at("t'accompagne")
def scene_cta(f, t):
    s_cta(f, t, T_CTA + 0.03, T_GO, T_ACC)
SCENES = [(d, fn if fn else scene_cta) for d, fn in SCENES]

# ---------- sous-titres karaoké ----------
ROUGES = {"iphone", "gratuit", "2k25", "majeur", "pc", "go", "gratuitement", "éligible", "tout", "toi", "18", "pro"}
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
        f = police(800, 56)
        esp = f.getlength(" ")
        lw = sum(f.getlength(w["t"]) for w in m) + esp * (len(m) - 1)
        tail = 56
        while lw > 790:
            tail -= 2; f = police(800, tail); esp = f.getlength(" ")
            lw = sum(f.getlength(w["t"]) for w in m) + esp * (len(m) - 1)
        p = out_expo(prog(t, debut, 0.25))
        d = ImageDraw.Draw(img)
        x = CX - lw / 2
        y = 1268 + (1 - p) * 20
        for w in m:
            if t >= w["s"] - 0.1:
                actif = w["s"] - 0.1 <= t < w["e"] + 0.05
                cle = w["t"].lower().strip(".,?!:") in ROUGES
                col = ROUGE if (actif or cle) else BLANC
                d.text((x, y), w["t"], font=f, fill=col, stroke_width=6, stroke_fill=NOIR)
            x += f.getlength(w["t"]) + esp

def rappel(img, t):
    if RAPPEL <= t < T_CTA:
        p = out_expo(prog(t, RAPPEL, 0.4))
        poser(img, pilule("COMMENTE GO", 34, BLANC, NOIR, 26, 12), CX, 1170 + (1 - p) * 30, 1, p)

# ---------- image ----------
def scene_index(t):
    i = 0
    for k, (d, fn) in enumerate(SCENES):
        if t >= d:
            i = k
    return i

def couche(i, t):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    SCENES[i][1](lay, t)
    return lay

TRANS = 0.32
def image(t):
    img = decor(t)
    i = scene_index(t)
    d0 = SCENES[i][0]
    if i > 0 and t - d0 < TRANS:
        p = (t - d0) / TRANS
        if p < 0.55:  # l'ancienne scène part en zoom flou
            q = p / 0.55
            poser(img, couche(i - 1, t), W / 2, H / 2, 1 + 0.18 * in_cubic(q), 1 - q, flou=14 * q)
        poser(img, couche(i, t), W / 2, H / 2, 0.9 + 0.1 * out_cubic(p), min(1, p * 1.6), flou=12 * (1 - p))
    else:
        img.alpha_composite(couche(i, t))
    rappel(img, t)
    pp = os.path.join(POLICES, "poppins-latin-800-normal.woff")
    tag_mobile(img, t, pp, T_CTA)
    signature(img, t, pp, T_ACC + 0.3)
    sous_titres(img, t)
    # punchs : flash blanc + secousse
    dx = dy = 0
    for pt in PUNCH:
        x = t - pt
        if 0 <= x < 0.25:
            a = int(70 * (1 - x / 0.25))
            img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, a)))
            amp = 14 * (1 - x / 0.25)
            dx, dy = int(math.sin(x * 90) * amp), int(math.cos(x * 70) * amp * 0.6)
    if dx or dy:
        sh = Image.new("RGBA", (W, H), NOIR + (255,))
        sh.paste(img, (dx, dy))
        img = sh
    # fondu d'entrée de 3 images (le hook est visible tout de suite)
    return img.convert("RGB")

if "--timeline" in sys.argv:  # instants clés pour synth_motion.py
    json.dump({"coupes": [d for d, _ in SCENES[1:]], "punchs": PUNCH, "coches": CHECKS, "entrees": ENTREES,
               "rappel": RAPPEL, "cta": T_CTA, "go": T_GO, "acc": T_ACC, "duree": DUREE},
              open(sys.argv[sys.argv.index("--timeline") + 1], "w"), indent=1)
    sys.exit()

if STILLS:
    for s in STILLS:
        image(s).save(os.path.join(os.path.dirname(SORTIE), f"still-{s:05.2f}.png"))
    sys.exit()

AUDIO = os.path.join(os.path.dirname(SORTIE), "mix.wav")
cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
       "-i", "-", "-i", AUDIO, "-c:v", "libx264", "-preset", "medium", "-b:v", "12M", "-maxrate", "14M",
       "-bufsize", "24M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", SORTIE]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for n in range(NF):
    p.stdin.write(image(n / FPS).tobytes())
p.stdin.close()
p.wait()
