"""Recolle la transcription mot à mot sur le texte réellement dit.

Usage : python3 corriger_mots.py <stt.json> <mots.json>
"""
import json, sys

d = json.load(open(sys.argv[1]))
mots = []
for w in d["words"]:
    if w["type"] != "word":
        continue
    if w["text"] in ("?", "!", ".", ",", ":") and mots:  # ponctuation isolée : rattachée au mot d'avant
        mots[-1] = dict(mots[-1], text=mots[-1]["text"] + w["text"], end=w["end"])
        continue
    mots.append(w)
FUSIONS = [  # suite de mots entendue -> mot affiché
    (["deux", "K", "vingt-cinq,"], "2K25,"),
    (["de", "K25."], "2K25."),
    (["de", "K25,"], "2K25,"),
    (["dix-huit"], "18"),
    (["Il", "n'y", "a"], "Y'a"),
    (["Il", "y", "a"], "Y'a"),
    (["Commande"], "Commente"),
    (["commandes"], "commentes"),
]
out, i = [], 0
while i < len(mots):
    for suite, mot in FUSIONS:
        if [w["text"] for w in mots[i:i + len(suite)]] == suite:
            out.append({"text": mot, "start": mots[i]["start"], "end": mots[i + len(suite) - 1]["end"], "type": "word"})
            i += len(suite)
            break
    else:
        out.append(mots[i])
        i += 1
d["words"] = out
d["text"] = " ".join(w["text"] for w in out)
json.dump(d, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
print(d["text"])
