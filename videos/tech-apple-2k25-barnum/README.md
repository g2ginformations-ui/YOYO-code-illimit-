# Tech Apple 2K25 — « Je lis dans ta tête » (effet Barnum + double twist)

Vidéo TikTok 9:16 (1080 × 1920, 30 i/s, 27,5 s), voix ElevenLabs « Maxime » (eleven_v4), tag @APPLE_PDG.

1. Hook : boule de cristal pixel, « JE LIS DANS TA TÊTE ».
2. La boule « devine » 4 traits qui collent à tout le monde (fenêtre « TON PROFIL » qui se coche).
3. Twist 1 : « JE T'AI EU — ça marche sur tout le monde » + tampon « EFFET BARNUM ».
4. Twist 2 : « mais ça, je le sais vraiment : t'as un PC ou un iPhone… tu me regardes DESSUS » (œil pixel).
5. « Si t'es majeur » → TECH APPLE 2K25 → IPHONE 18 PRO GRATUIT → CTA « COMMENTE GO » + signature.

Pas de montant ni de mécanisme ; seules conditions : majeur + un PC ou un iPhone.

- `texte.txt` : la voix, une phrase par ligne avec son émotion. `corriger_mots.py` → `mots.json`.
- `rendu.py` / `synth.py` : images et son (mêmes briques que `../tech-apple-2k25-hooks`).

```
python3 corriger_mots.py stt.json mots.json
python3 synth.py voix.wav out/mix.wav
python3 rendu.py voix.wav polices out/tech-apple-2k25-barnum.mp4
```
