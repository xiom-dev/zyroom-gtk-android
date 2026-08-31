# De quoi V-RyLune a l'air, et ce que chaque version a apporté

Ces fichiers viennent de l'arborescence `fastlane/` qu'exigeait F-Droid.
La démarche est abandonnée ; le contenu, lui, reste bon, et il est ici sous une
forme qui ne dépend plus de personne.

| | |
|---|---|
| `description-fr.md`, `description-en.md` | ce que fait l'application, pour qui la découvre |
| `captures/` | quatre captures d'écran (elles étaient en double, une par langue, alors qu'elles ne montrent rien de traduit) |
| `icone.png` | l'icône du lanceur, en grand format |
| `notes-de-version/{fr-FR,en-US}/<versionCode>.txt` | ce que chaque livraison a apporté |

Le numéro d'un fichier de note est un **versionCode**, pas un numéro de
version : c'est le seul numéro qu'Android ordonne, et le seul qui ne se répète
jamais. Certains manquent — `38.txt` par exemple — parce que la numérotation
saute quand elle repart du numéro publié plutôt que de celui du dépôt.

Rien ne lit ces fichiers automatiquement. `livraison.sh` rappelle seulement
d'écrire la note d'une livraison avant de construire, tant qu'on a encore en
tête ce qu'on vient de faire ; à défaut, personne ne le réécrira jamais.
