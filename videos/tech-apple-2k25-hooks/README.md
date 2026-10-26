# Tech Apple 2K25 — 3 variantes de hook (DA pixel noir et rouge)

Trois vidéos TikTok 9:16 (1080 × 1920, 30 i/s) à tester l'une contre l'autre. Même message, seul l'ordre change :
pas de montant ni de mécanisme, seulement les conditions (majeur + un PC ou un iPhone), l'iPhone 18 Pro gratuit
grâce à la tech Apple 2K25, et le CTA « COMMENTE GO » + « JE T'ACCOMPAGNE GRATUITEMENT ».
Un petit rappel « COMMENTE GO » reste affiché au-dessus des sous-titres dès la 2e ou 3e scène.

| Variante | Hook (première image) | Durée |
|---|---|---|
| A — résultat | « IPHONE 18 PRO » + « GRATUIT » | 14 s |
| B — secret | « PERSONNE N'EN PARLE » + « TECH APPLE 2K25 » | 17 s |
| C — question | « T'ES MAJEUR ? » + check-list à cocher | 14 s |

- `texte_<V>.txt` : la voix (ElevenLabs « Maxime », eleven_v4), une phrase par ligne avec son émotion.
- `corriger_mots.py` : recolle la transcription sur le texte dit (2K25, 18, Y'a, Commente).
- `mots_<V>.json` : instants des mots. `rendu.py` / `synth.py` : images et son, avec `--variante A|B|C`.

```
python3 corriger_mots.py stt_A.json mots_A.json
python3 synth.py voix_A.wav out/mix.wav --variante A
python3 rendu.py voix_A.wav polices out/tech-apple-2k25-A.mp4 --variante A
```

## Tag anti-copie

Chaque vidéo porte le tag de `../marque.json` (Solex2k25, @APPLE_PDG), dessiné par `../tag_marque.py` :
le @ semi-transparent change de place toutes les 2,5 s (haut et bas de la zone sûre), puis la signature
« SOLEX2K25 · @APPLE_PDG » s'affiche sous le CTA. Pour changer de nom ou de compte, modifier `marque.json`.
