# Tech Apple 2K25 — 3 vidéos en motion design (noir et rouge)

Vidéos TikTok 9:16 (1080 × 1920, **60 i/s**), voix ElevenLabs « Maxime » (eleven_v4), tag @le_a_poker.
Style motion design : Poppins grasse, ressorts et accélérations douces, transitions zoom + flou, lueurs,
punchs (flash + secousse) sur les moments forts, éclats de particules, coches qui se tracent,
téléphone dessiné (générique, sans logo), sous-titres karaoké, beat moderne (808, clap, charleston, nappe).

| Vidéo | Angle | Durée |
|---|---|---|
| 1 — rapide | iPhone 18 Pro GRATUIT d'abord → TECH APPLE 2K25 → « 2 choses » (cartes qui se cochent) → C'EST TOUT | 13,3 s |
| 2 — éligibilité | « ES-TU ÉLIGIBLE ? » → vérification → anneau 0 → 100 % → ÉLIGIBLE → iPhone 18 Pro | 13,7 s |
| 3 — compte à rebours | « DANS 3 SECONDES » → 3 (majeur) → 2 (PC ou iPhone) → 1 (iPhone 18 Pro) | 14,8 s |

Toutes finissent sur COMMENTE + pilule GO + bulle de commentaire qui s'écrit + « JE T'ACCOMPAGNE GRATUITEMENT »
+ signature. Pas de montant ; seules conditions : majeur + un PC ou un iPhone.

- `texte_<N>.txt` : la voix, une phrase par ligne avec son émotion. `corriger_mots.py` → `mots_<N>.json`.
- `motion.py` : le moteur d'images. `synth_motion.py` : le son, calé sur les instants exportés par `--timeline`.

```
python3 motion.py voix_1.wav polices x --video 1 --timeline out/tl.json
python3 synth_motion.py voix_1.wav out/tl.json out/mix.wav
python3 motion.py voix_1.wav polices out/tech-apple-2k25-motion-1.mp4 --video 1
```
Polices : Poppins 600 / 800 / 900 (`@fontsource/poppins` sur jsDelivr).
