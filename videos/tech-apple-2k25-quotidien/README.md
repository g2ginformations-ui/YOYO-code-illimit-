# Tech Apple 2k25 — version « chaque jour » (DA pixel noir et rouge)

Vidéo TikTok 9:16 (1080 × 1920, 30 i/s, 23 s), voix ElevenLabs « Maxime » (eleven_v4), même sujet que
`../tech-apple-2k25` : la carte cadeau quotidienne, la cagnotte qui monte, l'iPhone au bout de
quelques mois, l'achat-revente, puis le CTA « COMMENTE GO » + « JE T'ACCOMPAGNE GRATUITEMENT ».

- `texte.txt` : le texte de la voix, une phrase par ligne, avec la balise d'émotion.
- `mots.json` : transcription mot à mot de la voix assemblée (instants de chaque mot).
- `rendu.py` : les 7 scènes, calées sur les mots. `synth.py` : musique, bruitages et mixage (−14 LUFS).

## Refaire la voix

Chaque ligne de `texte.txt` → `POST /v1/text-to-speech/5Qfm4RqcAer0xoyWtoHC` (model `eleven_v4`), silences
coupés, accélérée ×1,1, 0,28 s entre les phrases, puis `POST /v1/speech-to-text` (scribe_v1, mots) → `mots.json`.
Phrase refaite après vérification : « Commente GO » (compris « Momente Go ») → « Écris GO en commentaire ».
Dans `mots.json`, trois découpages de la transcription sont recollés sur ce qui est dit :
« tu as » → « t'as », « tu achètes » → « t'achètes », « Il n'y a » → « Y'a ».

## Refaire le rendu

Polices : voir `../tech-apple-2k25/README.md`.

```
python3 synth.py voix.wav out/mix.wav
python3 rendu.py voix.wav polices out/tech-apple-2k25-quotidien.mp4
```
