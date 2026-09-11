# Sources des symboles

Les originaux dont sont tirées les icônes de menu, et les étapes qui y
mènent. Rien ici n'est lu par le code.

Ce que les applications chargent réellement se trouve ailleurs :

- `zyroom-gtk/zyroom/symboles/`
- `zyroom-qt/zyroom/symboles/`

Ces deux dossiers-là sont la version **livrée** : détourée, recadrée sur ce
qu'elle montre, à la taille attendue par l'application.

L'analogie web : c'est le `.psd` à côté du `.png` mis en ligne. La page
n'affiche que le second, mais perdre le premier veut dire tout refaire à la
prochaine retouche.

## Convention de nom

- `nom.png` — l'image d'origine, telle qu'elle vient du jeu : avec son cadre,
  son fond, sa taille
- `nom-net.png` — la même, détourée
- `nom-kaki.png` — une variante de teinte

**Le suffixe dit une étape, pas un travail en attente.** C'est le piège de ce
dossier, et il a déjà fait perdre du temps : voyant `coffre-net.png` sans
équivalent dans les applications, on conclut qu'un détourage attend d'être
intégré. Il ne l'attend pas — il *est* l'icône livrée, qui porte simplement le
nom `coffre.png`. Mesuré : l'écart entre `coffre-net.png` et le `coffre.png`
livré, une fois l'un et l'autre recadrés et ramenés à la même taille, est
exactement nul. De même pour `inventaire`, `mektoub`, `zig`, et pour la bourse
`dappers-kaki`.

Autrement dit, deux fichiers de même nom des deux côtés **doivent** différer :
à gauche l'original avec son cadre, à droite le dessin nu. Comparer leurs
octets ne dit rien ; ce qui se compare, ce sont les dessins, une fois le
transparent rogné.

Quand une source part vers une application, elle est recopiée, pas déplacée :
l'exemplaire reste ici.
