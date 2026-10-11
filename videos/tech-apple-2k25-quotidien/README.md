# Tech Apple 2k25 — version « chaque jour » (DA pixel noir et rouge)

Vidéo TikTok 9:16 (1080 × 1920, 30 i/s, 26 s), voix ElevenLabs « Maxime » (eleven_v4), même sujet que
`../tech-apple-2k25` : la carte cadeau quotidienne (1 € à 20 €), la cagnotte qui monte, l'iPhone au bout de
quelques mois, l'achat-revente, puis le CTA « COMMENTE GO » + « JE T'ACCOMPAGNE GRATUITEMENT ».

- `texte.txt` : le texte de la voix, une phrase par ligne, avec la balise d'émotion.
- `mots.json` : transcription mot à mot de la voix assemblée (instants de chaque mot).
- `rendu.py` : les 8 scènes, calées sur les mots. `synth.py` : musique, bruitages et mixage (−14 LUFS).

## Refaire la voix

Chaque ligne de `texte.txt` → `POST /v1/text-to-speech/5Qfm4RqcAer0xoyWtoHC` (model `eleven_v4`), silences
coupés, accélérée ×1,1, 0,28 s entre les phrases, puis `POST /v1/speech-to-text` (scribe_v1, mots) → `mots.json`.
Phrases refaites après vérification : « Entre un et vingt euros » (compris « Rentre ») et « Commente GO »
(compris « Momente Go ») ; d'où « Ça va d'un euro à vingt euros » et « Écris GO en commentaire ».

## Refaire le rendu

Polices : voir `../tech-apple-2k25/README.md`.

```
python3 synth.py voix.wav out/mix.wav
python3 rendu.py voix.wav polices out/tech-apple-2k25-quotidien.mp4
```
