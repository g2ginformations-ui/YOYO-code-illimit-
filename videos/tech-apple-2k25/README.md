# Tech Apple 2k25 — DA pixel noir et rouge

Vidéo TikTok 9:16 (1080 × 1920, 30 i/s, 12 s) : la voix d'origine, posée sur le décor pixel
(halo rouge, poussières, lignes de balayage, glitchs, tampons, chiptune).

- `tech-apple-2k25.mp4` : la vidéo finie (−14 LUFS).
- `mots.json` : transcription mot à mot de la voix (instants de chaque mot).
- `rendu.py` : les images, calées sur les mots. `synth.py` : musique, bruitages et mixage.

## Refaire le rendu

```
ffmpeg -i video-source.mp4 -vn -ac 1 -ar 44100 voix.wav
mkdir polices && cd polices
curl -LO https://cdn.jsdelivr.net/npm/@fontsource/silkscreen@5.0.8/files/silkscreen-latin-700-normal.woff
curl -LO https://cdn.jsdelivr.net/npm/@fontsource/poppins@5.0.8/files/poppins-latin-800-normal.woff
cd ..
mkdir -p out
python3 synth.py voix.wav out/mix.wav
python3 rendu.py voix.wav polices out/tech-apple-2k25.mp4
python3 rendu.py voix.wav polices out/x.mp4 --stills 0.5,4.2,8,11   # images de contrôle
```
