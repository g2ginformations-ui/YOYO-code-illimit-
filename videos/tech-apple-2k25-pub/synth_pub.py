"""Son des vidéos motion design : voix + beat moderne + bruitages, calés sur les instants de motion.py.

Usage : python3 synth_motion.py <voix.wav> <timeline.json> <mix.wav>
  (timeline.json : python3 motion.py <voix> <polices> <x> --video N --timeline timeline.json)
Le mix sort à -14 LUFS, crête -1 dB (norme TikTok).
"""
import json, os, subprocess, sys, wave
import numpy as np

VOIX, TIMELINE, SORTIE = sys.argv[1], sys.argv[2], sys.argv[3]
SR = 44100
TL = json.load(open(TIMELINE))

def lufs(f):
    e = subprocess.run(["ffmpeg", "-hide_banner", "-i", f, "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return float(e[e.rindex("I:"):].split()[1])

# --- voix nettoyée, compressée, calée à -15 LUFS avant le mixage ---
prep = SORTIE + ".voix.wav"
chaine = "highpass=f=80,acompressor=threshold=-30dB:ratio=4:attack=5:release=120:makeup=1"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", VOIX, "-af", chaine, "-ac", "1", "-ar", str(SR), prep], check=True)
g = -15 - lufs(prep)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", VOIX, "-af", f"{chaine},volume={g:.2f}dB,alimiter=limit=0.89:level=false",
                "-ac", "1", "-ar", str(SR), prep], check=True)
with wave.open(prep) as wf:
    voix = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32) / 32768
os.remove(prep)
N = int(TL["duree"] * SR)
voix = np.concatenate([voix, np.zeros(max(0, N - len(voix)), np.float32)])[:N]

rng = np.random.default_rng(4)
def tt(d):
    return np.arange(int(d * SR)) / SR
def hz(n):
    return 440 * 2 ** ((n - 69) / 12)
def env(x, a=0.005, r=0.1):
    n = len(x); e = np.ones(n)
    na, nr = min(n, int(a * SR)), min(n, int(r * SR))
    e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return x * e
def passe_bas(x, k):
    """Filtre passe-bas à un pôle (k entre 0 et 1, ou tableau)."""
    y = np.zeros_like(x)
    k = np.broadcast_to(k, x.shape)
    acc = 0.0
    for i in range(len(x)):
        acc += k[i] * (x[i] - acc)
        y[i] = acc
    return y
def ajoute(piste, t0, x, g=1.0):
    i = int(t0 * SR)
    if i >= len(piste) or i + len(x) <= 0:
        return
    if i < 0:
        x, i = x[-i:], 0
    x = x[: len(piste) - i]
    piste[i:i + len(x)] += x * g

# --- beat : 100 BPM, la m / fa / do / sol ---
BEAT = 0.6
musique = np.zeros(N)
ACC = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)]
def kick():
    x = tt(0.45)
    f = 45 + 110 * np.exp(-x * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 7)
def clap():
    x = tt(0.18)
    n = rng.uniform(-1, 1, len(x))
    return passe_bas(n, 0.5) * np.exp(-x * 22) * 0.8
def hat(ouvert=False):
    x = tt(0.12 if ouvert else 0.04)
    n = rng.uniform(-1, 1, len(x))
    return (n - passe_bas(n, 0.3)) * np.exp(-x * (25 if ouvert else 90))
def nappe(notes, d):
    x = tt(d)
    s = sum(((x * hz(n) * (1 + det)) % 1) * 2 - 1 for n in notes for det in (-0.004, 0.004))
    s = passe_bas(s / (2 * len(notes)), 0.06)
    return env(s, 0.3, 0.4)
mesure = 4 * BEAT
nb = int(TL["duree"] / mesure) + 1
for m in range(nb):
    t0 = m * mesure
    notes = ACC[m % 4]
    ajoute(musique, t0, nappe(notes, mesure), 0.35)
    ajoute(musique, t0, env(np.sin(2 * np.pi * hz(notes[0] - 24) * tt(mesure * 0.95)), 0.01, 0.2), 0.35)  # sub
    for b in range(4):
        tb = t0 + b * BEAT
        if b in (0, 2) or (b == 3 and m % 2):
            ajoute(musique, tb + (BEAT / 2 if b == 3 else 0), kick(), 0.9)
        if b in (1, 3):
            ajoute(musique, tb, clap(), 0.5)
        for k in range(4):
            ajoute(musique, tb + k * BEAT / 4, hat(k == 2 and b == 3), 0.18 if k % 2 else 0.28)
fondu = int(0.8 * SR)
musique[-fondu:] *= np.linspace(1, 0, fondu)

# --- bruitages ---
sfx = np.zeros(N)
def whoosh(d=0.4):
    x = tt(d)
    n = rng.uniform(-1, 1, len(x))
    k = 0.02 + 0.35 * np.sin(np.pi * x / d) ** 2
    return passe_bas(n, k) * np.sin(np.pi * x / d) * 0.9
def impact():
    x = tt(0.8)
    boom = np.sin(2 * np.pi * np.cumsum(40 + 60 * np.exp(-x * 12)) / SR) * np.exp(-x * 4)
    souffle = passe_bas(rng.uniform(-1, 1, len(x)), 0.15) * np.exp(-x * 9) * 0.5
    return (boom + souffle) * 0.9
def montee(d=0.6):
    x = tt(d)
    n = rng.uniform(-1, 1, len(x))
    return passe_bas(n, 0.02 + 0.5 * (x / d) ** 2) * (x / d) ** 2 * 0.6
def pop():
    x = tt(0.09)
    return np.sin(2 * np.pi * np.cumsum(500 + 900 * x / 0.09) / SR) * np.exp(-x * 40) * 0.6
def ding():
    x = tt(0.6)
    return (np.sin(2 * np.pi * 1568 * x) + 0.5 * np.sin(2 * np.pi * 2349 * x)) * np.exp(-x * 7) * 0.25
def tic():
    x = tt(0.03)
    return rng.uniform(-1, 1, len(x)) * np.exp(-x * 200) * 0.3

for c in TL["coupes"]:
    ajoute(sfx, c - 0.18, whoosh())
for p in TL["punchs"]:
    ajoute(sfx, p - 0.6, montee())
    ajoute(sfx, p, impact())
for e in TL["entrees"]:
    ajoute(sfx, e, whoosh(0.3), 0.6)
for c in TL["coches"]:
    ajoute(sfx, c, pop()); ajoute(sfx, c + 0.05, ding())
ajoute(sfx, TL["rappel"], pop(), 0.6)
ajoute(sfx, TL["go"], pop())
for k in range(2):
    ajoute(sfx, TL["go"] + 0.2 + k * 0.1, tic())
ajoute(sfx, TL["go"] + 0.5, ding())
ajoute(sfx, TL["acc"], pop(), 0.8)

# --- mixage : la voix devant ---
ev = np.convolve(np.abs(voix), np.ones(int(0.15 * SR)) / int(0.15 * SR), mode="same")
sous_voix = np.clip(ev / 0.02, 0, 1)
mix = voix + musique * 0.2 * (1 - 0.6 * sous_voix) + sfx * 0.4
mix[-fondu:] *= np.linspace(1, 0, fondu)
mix = np.clip(mix / max(1.0, np.abs(mix).max()), -1, 1)
brut = SORTIE + ".brut.wav"
with wave.open(brut, "wb") as wf:
    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
    wf.writeframes((mix * 32767).astype(np.int16).tobytes())
gain = -14 - lufs(brut)
for _ in range(5):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", brut, "-af",
                    f"volume={gain:.2f}dB,alimiter=limit=0.84:level=false,aresample=44100", "-ac", "2", SORTIE], check=True)
    ecart = -14 - lufs(SORTIE)
    if abs(ecart) < 0.1:
        break
    gain += ecart
os.remove(brut)
