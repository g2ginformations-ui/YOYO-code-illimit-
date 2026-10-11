# Tech Apple 2025 — sur ton script (DA pixel noir et rouge)

Vidéo TikTok 9:16 (1080 × 1920, 30 i/s, 21 s), voix ElevenLabs « Maxime » (eleven_v4), 6 scènes :
hook « TECH APPLE 2025 » → les conditions (majeur, un PC ou un iPhone) → carte cadeau gratuite →
mode d'emploi (dépense, achète, revends) → « Y'A PAS PLUS SIMPLE » ×2 → CTA « COMMENTE GO » +
« JE T'ACCOMPAGNE GRATUITEMENT ».

- `texte.txt` : le texte de la voix, une phrase par ligne, avec la balise d'émotion.
- `corriger_mots.py` : recolle la transcription sur le texte dit (« deux mille vingt-cinq » → « 2025 »,
  « Il n'y a » → « Y'a », « Commande » → « Commente », fausse alerte connue de la transcription).
- `mots.json` : instants de chaque mot. `rendu.py` : les images. `synth.py` : musique, bruitages, mixage (−14 LUFS).

## Refaire

Voix : chaque ligne de `texte.txt` → `POST /v1/text-to-speech/5Qfm4RqcAer0xoyWtoHC` (eleven_v4), silences coupés,
×1,1, 0,28 s entre les phrases ; puis `POST /v1/speech-to-text` (scribe_v1, mots) → `stt.json`.
Polices : voir `../tech-apple-2k25/README.md`.

```
python3 corriger_mots.py stt.json mots.json
python3 synth.py voix.wav out/mix.wav
python3 rendu.py voix.wav polices out/tech-apple-2025.mp4
```
