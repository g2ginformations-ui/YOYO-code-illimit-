"""Son de Tech Apple 2k25, version « chaque jour » : voix ElevenLabs + chiptune + bruitages, calés sur les mêmes mots que rendu.py.

Usage : python3 synth.py <voix.wav> <mix.wav>
Le mix sort à -14 LUFS, crête -1 dB (norme TikTok).
"""
import json, os, subprocess, sys, wave
import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
VOIX, SORTIE = sys.argv[1], sys.argv[2]
SR = 44100

CTA = 2.0  # secondes tenues sur la fin « COMMENTE GO » après la voix (même valeur dans rendu.py)

def lufs(f):
    e = subprocess.run(["ffmpeg", "-hide_banner", "-i", f, "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return float(e[e.rindex("I:"):].split()[1])

# On nettoie, compresse et cale la voix à -15 LUFS AVANT le mixage, pour qu'elle passe devant
# la musique et les bruitages.
VOIX_PREP = SORTIE + ".voix.wav"
chaine = "highpass=f=80,acompressor=threshold=-30dB:ratio=4:attack=5:release=120:makeup=1"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", VOIX, "-af", chaine, "-ac", "1", "-ar", str(SR), VOIX_PREP], check=True)
g = -15 - lufs(VOIX_PREP)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", VOIX, "-af",
                f"{chaine},volume={g:.2f}dB,alimiter=limit=0.89:level=false", "-ac", "1", "-ar", str(SR), VOIX_PREP], check=True)
with wave.open(VOIX_PREP) as wf:
    voix = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32) / 32768
os.remove(VOIX_PREP)
FIN_VOIX = len(voix) / SR
voix = np.concatenate([voix, np.zeros(int(CTA * SR), np.float32)])
N = len(voix)
DUREE = N / SR

MOTS = [w for w in json.load(open(os.path.join(ICI, "mots.json")))["words"] if w["type"] == "word"]
def at(txt, n=1):
    k = 0
    for m in MOTS:
        if m["text"].lower().strip(".,").startswith(txt.lower()):
            k += 1
            if k == n:
                return m["start"]
    raise KeyError(txt)

def tt(d):
    return np.arange(int(d * SR)) / SR
def carre(f, d, duty=0.5):
    return np.where((tt(d) * f) % 1 < duty, 1.0, -1.0)
def tri(f, d):
    return 2 * np.abs(2 * ((tt(d) * f) % 1) - 1) - 1
def env(x, a=0.005, r=0.08):
    n = len(x)
    e = np.ones(n)
    na, nr = min(n, int(a * SR)), min(n, int(r * SR))
    e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return x * e
def hz(note):
    return 440 * 2 ** ((note - 69) / 12)

def ajoute(piste, t0, x, g=1.0):
    i = int(t0 * SR)
    if i >= len(piste) or i + len(x) <= 0:
        return
    if i < 0:
        x, i = x[-i:], 0
    x = x[: len(piste) - i]
    piste[i:i + len(x)] += x * g

# ---------- musique ----------
musique = np.zeros(N)
BEAT = 0.5
# A (tendu) : la m, fa, ré m, mi — puis C (majeur) : do, sol, la m, fa
ACC = {"Am": (57, 60, 64), "F": (53, 57, 60), "Dm": (50, 53, 57), "E": (52, 56, 59),
       "C": (48, 52, 55), "G": (55, 59, 62)}
# A (tendu) x2, B x2, puis C (majeur, avec mélodie) jusqu'à la fin ; 1 accord = 2 temps
GRILLE = ["Am", "F", "Dm", "E"] * 2 + ["Am", "G", "F", "G"] * 2 + ["C", "G", "Am", "F"] * 3
MELO = [76, 74, 72, 74, 76, 79, 76, 72]
for b, nom in enumerate(GRILLE):
    t0 = b * 2 * BEAT
    if t0 >= DUREE - 1.0:
        break
    notes = ACC[nom]
    for k in range(8):  # arpège carré en doubles-croches
        n = notes[k % 3] + 12 * (k // 3 % 2)
        ajoute(musique, t0 + k * BEAT / 4, env(carre(hz(n + 12), BEAT / 4 * 0.9, 0.25), r=0.03), 0.10)
    for k in range(4):  # basse triangle en croches
        ajoute(musique, t0 + k * BEAT / 2, env(tri(hz(notes[0] - 12), BEAT / 2 * 0.9), r=0.04), 0.30)
    for k in range(2):  # grosse caisse sur 1 et 3, charleston à contretemps
        tb = t0 + k * BEAT
        x = tt(0.12)
        ajoute(musique, tb, np.sin(2 * np.pi * (110 - 400 * x) * x) * np.exp(-x * 30), 0.6)
        h = np.random.default_rng(b * 2 + k).uniform(-1, 1, int(0.03 * SR))
        ajoute(musique, tb + BEAT / 2, env(np.diff(h, prepend=0), r=0.02), 0.08)
    if b >= 16:  # mélodie sur la partie C
        for k in range(2):
            ajoute(musique, t0 + k * BEAT, env(carre(hz(MELO[(b * 2 + k) % 8]), BEAT * 0.8, 0.5), r=0.06), 0.06)

# ---------- bruitages ----------
sfx = np.zeros(N)
rng = np.random.default_rng(1)
def ppop():
    x = tt(0.07)
    return env(np.where((x * (500 + 6000 * x)) % 1 < 0.5, 1, -1), r=0.03) * 0.25
def stamp():
    x = tt(0.25)
    return (np.sin(2 * np.pi * (90 - 120 * x) * x) * np.exp(-x * 18) + rng.uniform(-1, 1, len(x)) * np.exp(-x * 60) * 0.4) * 0.9
def glitch(d=0.15):
    x = rng.uniform(-1, 1, int(d * SR))
    x = np.repeat(x[::40], 40)[: int(d * SR)]  # « bitcrush »
    return env(np.round(x * 4) / 4, r=0.02) * 0.25
def ping():
    out = np.zeros(int(0.3 * SR))
    for k, n in enumerate((83, 88)):  # si puis mi
        c = env(carre(hz(n), 0.12, 0.5), r=0.05) * 0.12
        i = int(k * 0.1 * SR)
        out[i:i + len(c)] += c
    return out
def click():
    x = tt(0.03)
    return env(carre(2400, 0.03), r=0.02) * 0.15
def impact():
    x = tt(0.6)
    return np.sin(2 * np.pi * (70 - 50 * x) * x) * np.exp(-x * 6) * 0.9
def chime():
    out = np.zeros(int(0.5 * SR))
    for k, n in enumerate((84, 88, 91)):
        c = env(carre(hz(n), 0.25, 0.25), r=0.15) * 0.12
        i = int(k * 0.07 * SR)
        out[i:i + len(c)] += c[: len(out) - i]
    return out
def typer(d):
    out = np.zeros(int(d * SR))
    for k in range(int(d / 0.05)):
        b = env(carre(1700 + 120 * (k % 3), 0.025), r=0.01) * 0.06
        i = int(k * 0.05 * SR)
        out[i:i + len(b)] += b
    return out
def riseblips():
    out = np.zeros(int(0.45 * SR))
    for k in range(10):
        b = env(carre(hz(72 + k * 2), 0.035), r=0.01) * 0.08
        i = int(k * 0.04 * SR)
        out[i:i + len(b)] += b
    return out
def whoosh():
    x = tt(0.35)
    n = rng.uniform(-1, 1, len(x))
    # bruit filtré qui monte puis redescend
    k = np.clip(0.02 + 0.3 * np.sin(np.pi * x / 0.35), 0, 1)
    y = np.zeros_like(n)
    for i in range(1, len(n)):
        y[i] = y[i - 1] + k[i] * (n[i] - y[i - 1])
    return y * np.sin(np.pi * x / 0.35) * 0.5

def coupe(mot, n=1):
    return at(mot, n) - 0.15
C2, C3, C4, C5, C6, C7 = coupe("chaque"), coupe("ça"), coupe("tu"), coupe("et"), coupe("ou"), coupe("c'est")
T_CTA = coupe("écris")  # mêmes instants que rendu.py
T_TEL = at("iphone") - 0.08
STOPS = [at("carte") - 0.08 + k * 0.14 for k in range(3)]
L1, L2, L3 = at("t'achètes") - 0.08, at("sur") - 0.08, at("revends") - 0.08
for t0, x in [
    (0.0, glitch()), (0.0, ppop()),
    (at("personne") - 0.08, stamp()),
    (C2 - 0.1, whoosh()), (C2, glitch(0.12)), (C2 + 0.1, ppop()),
    *[(s0, click()) for s0 in STOPS], (STOPS[2] + 0.2, chime()),
    (C3 - 0.1, whoosh()), (C3, glitch(0.12)), (C3 + 0.07, ppop()), (at("euro") - 0.08, ppop()),
    (at("vingt") - 0.08, riseblips()), (at("gratuitement") - 0.08, stamp()),
    (C4 - 0.1, whoosh()), (C4, glitch(0.12)), (C4 + 0.1, ppop()), (at("cumules") - 0.08, riseblips()),
    (at("sans") - 0.08, stamp()),
    (C5 - 0.1, whoosh()), (C5, glitch(0.12)), (T_TEL, impact()), (T_TEL, glitch()), (T_TEL + 0.1, chime()),
    (at("gratuit", 2) - 0.08, stamp()),
    (C6 - 0.1, whoosh()), (C6, glitch(0.12)), (C6 + 0.1, ppop()),
    (L1, typer(0.45)), (L2, typer(0.45)), (L3, typer(0.3)), (L3 + 0.1, riseblips()),
    (C7 - 0.1, whoosh()), (C7, glitch(0.12)), (C7, ppop()), (at("pas") - 0.08, stamp()),
    (T_CTA - 0.1, whoosh()), (T_CTA, glitch(0.12)), (T_CTA, ppop()), (at("go") - 0.08, ping()),
    (at("go") + 0.22, typer(0.25)), (at("t'accompagne") - 0.08, ppop()), (at("t'accompagne") + 0.1, chime()),
]:
    ajoute(sfx, t0, x)

# ---------- mixage ----------
# la voix devant : musique discrète (encore baissée sous la voix), bruitages légers
ev = np.convolve(np.abs(voix), np.ones(int(0.15 * SR)) / int(0.15 * SR), mode="same")
sous_voix = np.clip(ev / 0.02, 0, 1)
mix = voix + musique * 0.16 * (1 - 0.6 * sous_voix) + sfx * 0.45
fondu = int(0.8 * SR)
mix[-fondu:] *= np.linspace(1, 0, fondu)
mix = np.clip(mix / max(1.0, np.abs(mix).max()), -1, 1)

brut = SORTIE + ".brut.wav"
with wave.open(brut, "wb") as wf:
    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
    wf.writeframes((mix * 32767).astype(np.int16).tobytes())

# normalisation -14 LUFS : gain mesuré, puis limiteur à -1 dB de crête
gain = -14 - lufs(brut)
for _ in range(5):  # le limiteur mange un peu de volume : on rattrape
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", brut, "-af",
                    f"volume={gain:.2f}dB,alimiter=limit=0.84:level=false,aresample=44100",
                    "-ac", "2", SORTIE], check=True)
    ecart = -14 - lufs(SORTIE)
    if abs(ecart) < 0.1:
        break
    gain += ecart
os.remove(brut)
