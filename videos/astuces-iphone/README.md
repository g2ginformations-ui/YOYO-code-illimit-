# Astuces iPhone sans visage — 5 vidéos (motion design, iPhone dessiné)

1080 × 1920, 30 i/s, voix ElevenLabs « Maxime » (eleven_v4), tag @APPLE_PDG. iPhone générique dessiné (aucun logo),
écrans façon réglages / clavier / appareil photo, toucher animés, zooms sur les détails, bandeaux, sous-titres
karaoké sur pastille sombre, carte question finale avec champ de commentaire.

| Fichier | Astuce | Durée |
|---|---|---|
| `astuce-1.mp4` | Toucher le dos (Réglages › Accessibilité › Toucher › Toucher le dos) | 17,8 s |
| `astuce-2.mp4` | Appui long sur la barre d'espace = trackpad | 12,6 s |
| `astuce-3.mp4` | 3 réglages batterie (actualisation, services système, analyses) | 18,7 s |
| `astuce-4.mp4` | Texte en direct dans l'appareil photo (mot de passe Wi-Fi) | 14,3 s |
| `astuce-5.mp4` | Avis tranché : changer d'iPhone chaque année ? | 11,5 s |

Légendes prêtes à coller : `DESCRIPTIONS.md`. Les noms de menus suivent iOS récent ; à vérifier sur ta version.

```
python3 astuces.py voix_1.wav polices x --video 1 --timeline out/tl.json
python3 synth_astuces.py voix_1.wav out/tl.json out/mix.wav
python3 astuces.py voix_1.wav polices out/astuce-1.mp4 --video 1
```
