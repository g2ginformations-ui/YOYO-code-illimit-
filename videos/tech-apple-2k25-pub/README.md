# Tech Apple 2K25 — 4 vidéos format « pub » (fonds pleins noir / rouge)

Inspirées du langage des pubs « compte en 5 minutes » fournies en référence : fonds pleins qui alternent à chaque
mot, police condensée très grasse (Anton) plein écran, mots qui « tapent », mots barrés, listes qui s'empilent,
texte en relief penché avec rayons et étoiles, téléphones en éventail, fin avec curseur qui clique. Rouge à la place
de leur orange, aucun logo ni nom de marque repris. 1080 × 1920, 30 i/s, voix « Maxime » (eleven_v4), tag @le_a_poker.

| Vidéo | Idée | Durée |
|---|---|---|
| 1 — Sans | ~~PRISE DE TÊTE~~ ~~CRAVATE~~ ~~TE RUINER~~ → TECH APPLE 2K25 → iPhone 18 Pro → 1. MAJEUR 2. PC OU IPHONE → « ça doit pas coûter cher » | 16,9 s |
| 2 — Bravo | BRAVO / LE BON PLAN / COOL / LE PLUS COURT → « fais pareil pour ton iPhone » → téléphones en éventail → MAJEUR ? PC OU IPHONE ? C'EST TOUT. | 16,9 s |
| 3 — 1·1·1 | 1 MAJEUR / 1 PC OU 1 IPHONE / 1 COMMENTAIRE → POUR 1 IPHONE 18 PRO → TOUT SIMPLEMENT | 12,3 s |
| 4 — Partout | lit / bus / livres → PARTOUT → il te faut juste… → iPhone 18 Pro | 14,3 s |

Fin commune : COMMENTE + champ « GO » cliqué par un curseur + JE T'ACCOMPAGNE GRATUITEMENT + signature.
Descriptions prêtes à coller : `DESCRIPTIONS.md`.

```
python3 pub.py voix_1.wav polices x --video 1 --timeline out/tl.json
python3 synth_pub.py voix_1.wav out/tl.json out/mix.wav
python3 pub.py voix_1.wav polices out/tech-apple-2k25-pub-1.mp4 --video 1
```
Polices : Anton 400 et Poppins 800 (`@fontsource` sur jsDelivr).
