# Sources des symboles

Originaux et retouches des icônes de menu, avant intégration dans les
applications.

Ce que les applications chargent réellement se trouve ailleurs :

- `zyroom-gtk/zyroom/symboles/`
- `zyroom-qt/zyroom/symboles/`

Ces deux dossiers-là sont la version **livrée** : recadrée, recompressée,
au format attendu par l'application. Le présent dossier garde ce qui a servi
à les fabriquer — l'image d'origine, une variante essayée, une version
nettoyée en attente d'intégration. Rien ici n'est lu par le code.

L'analogie web : c'est le `.psd` à côté du `.png` mis en ligne. La page
n'affiche que le second, mais perdre le premier veut dire tout refaire à la
prochaine retouche.

## Convention de nom

- `nom.png` — l'original ou la dernière retouche en date
- `nom-net.png` — version nettoyée (fond détouré)
- `nom-kaki.png` — variante de teinte

Quand une source part vers une application, elle est recopiée, pas déplacée :
l'exemplaire reste ici.
