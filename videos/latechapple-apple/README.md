# La tech Apple 2K25 — motion design « keynote »

Vidéo TikTok 9:16 (1080 × 1920, 60 i/s, 12,4 s), voix ElevenLabs « Maxime » (eleven_v4), tag @APPLE_PDG.
Fond clair, grand texte noir (Poppins), une seule touche de rouge, entrées en fondu qui montent, transitions
zoom-fondu, iPhone dessiné (générique, sans logo), cartes blanches avec ombre, son doux (pas de beat).

Texte : « La tech Apple 2K25. Un iPhone 18 Pro. Offert. Deux conditions : être majeur, un PC ou un iPhone.
C'est tout. Commente go, et je t'accompagne. »

- `texte.txt` : la voix, une phrase par ligne avec son émotion. `corriger_mots.py` → `mots.json`.
- `apple.py` : les images. `synth_apple.py` : le son (nappe douce, petits dings, voix à −14 LUFS).

```
python3 apple.py voix.wav polices x --timeline out/tl.json
python3 synth_apple.py voix.wav out/tl.json out/mix.wav
python3 apple.py voix.wav polices out/latechapple-apple.mp4
```
