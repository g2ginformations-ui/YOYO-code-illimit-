"""Tag anti-copie commun à toutes les vidéos : nom + @ Instagram, lus dans marque.json.

- tag mobile : « @APPLE_PDG », semi-transparent, qui saute d'une place à l'autre toutes les 2,5 s
  (en haut puis en bas de la zone sûre, à gauche, au centre, à droite) : on ne peut pas le recadrer
  ni l'effacer d'un seul coup ;
- signature : « SOLEX2K25 · @APPLE_PDG » sous le CTA final.
Jamais sur la bande des sous-titres (y 1215 à 1360).
"""
import json, os
from PIL import Image, ImageDraw, ImageFont

ICI = os.path.dirname(os.path.abspath(__file__))
MARQUE = json.load(open(os.path.join(ICI, "marque.json")))
NOM = MARQUE["nom"].upper()
HANDLE = "@" + MARQUE["handle"].upper()

# places du tag mobile (centre x, centre y) : bande du haut (au-dessus des titres) et du bas (sous les sous-titres)
PLACES = [(330, 300), (710, 1405), (520, 300), (330, 1405), (710, 300), (520, 1405)]
PERIODE = 2.5

_cache = {}
def _img(txt, police, size, col, alpha):
    k = (txt, size, col, alpha)
    if k not in _cache:
        f = ImageFont.truetype(police, size)
        w = int(f.getlength(txt)) + 8
        im = Image.new("RGBA", (w, size + 12), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        # contour noir 2 px pour rester lisible sur tout fond
        for dx in (-2, 0, 2):
            for dy in (-2, 0, 2):
                d.text((4 + dx, 4 + dy), txt, font=f, fill=(7, 3, 3, alpha))
        d.text((4, 4), txt, font=f, fill=col + (alpha,))
        _cache[k] = im
    return _cache[k]

def tag_mobile(img, t, police, t_fin=None):
    """Le @ qui change de place ; coupé à t_fin (début du CTA, où la signature prend le relais)."""
    if t_fin is not None and t >= t_fin:
        return
    x, y = PLACES[int(t / PERIODE) % len(PLACES)]
    el = _img(HANDLE, police, 36, (244, 241, 236), 150)
    img.alpha_composite(el, (int(x - el.width / 2), int(y - el.height / 2)))

def signature(img, t, police, t0, cx=520, y=1185):
    """Nom + @ en clair sous le CTA, à partir de t0."""
    if t < t0:
        return
    el = _img(f"{NOM} · {HANDLE}", police, 40, (244, 241, 236), 255)
    img.alpha_composite(el, (int(cx - el.width / 2), int(y - el.height / 2)))
