# La recette F-Droid

`net.ryzom.zyroom.yml` est la **recette de construction** que F-Droid attend.
Elle ne sert à rien dans ce dépôt-ci : sa place est dans le leur,
`fdroiddata/metadata/net.ryzom.zyroom.yml`. Elle est gardée ici pour qu'on
puisse la relire, la corriger et la renvoyer sans la réécrire de mémoire.

## Pourquoi une recette, alors qu'une demande existe déjà

La demande [RFP #4244](https://gitlab.com/fdroid/rfp/-/issues/4244) n'est qu'un
vœu déposé dans une file. Le robot qui l'a examinée est passé **une seule
fois**, le 10 août 2026 à 12 h 04, et ne repassera pas : ses remarques — et ses
étiquettes — décrivent le dépôt de ce matin-là. Rien ne le relance, ni un
commentaire, ni un changement de code.

Tant que personne n'écrit la recette, **rien ne construit l'application et
personne ne lit `fastlane/`** : ces métadonnées-là sont lues par
`fdroidserver` au moment de la construction, pas par le robot de la file. Une
demande peut y dormir des mois. Proposer soi-même la recette est le chemin
court.

## Comment l'envoyer

1. Forker `https://gitlab.com/fdroid/fdroiddata` sur GitLab.
2. Y déposer le fichier sous `metadata/net.ryzom.zyroom.yml`.
3. Vérifier avec leurs outils. Ils s'installent sans rien toucher au système :

       python3 -m venv /tmp/venv-fdroid
       /tmp/venv-fdroid/bin/pip install fdroidserver
       /tmp/venv-fdroid/bin/fdroid readmeta
       /tmp/venv-fdroid/bin/fdroid lint net.ryzom.zyroom
       /tmp/venv-fdroid/bin/fdroid rewritemeta net.ryzom.zyroom

   Il faut les lancer **depuis une copie de `fdroiddata`**, ou depuis un
   dossier qui lui ressemble : `config.yml`, `config/categories.yml` et
   `metadata/`. Sans le fichier des catégories, le contrôle des catégories se
   trompe — et sans les icônes qu'il mentionne, il s'interrompt en pleine
   course.

   Une liste réduite aux seuls noms ne suffit plus : `fdroidserver` 2.4.5 la
   lit comme une suite de valeurs vides et s'arrête sur un `AttributeError`,
   loin de la vraie cause. Chaque catégorie veut un nom traduit :

       Game Helper:
         name:
           en-US: Game Helper
       Inventory:
         name:
           en-US: Inventory

   Ce contrôle a déjà servi : la recette annonçait la catégorie `Games`, qui
   **n'existe plus**. F-Droid en tient aujourd'hui cent huit, bien plus fines.
   Retenues ici : `Game Helper` — l'application accompagne un jeu sans en être
   un — et `Inventory`.

   Mais il ne remplace pas leur intégration continue, qui en a trouvé deux de
   plus (le 17 août) : le `scandelete` inutile expliqué plus bas, et un simple
   **repli de ligne**. Leur version de `rewritemeta` veut la longue valeur de
   `UpdateCheckData` renvoyée à la ligne suivante, indentée de deux espaces.

   **Ne pas reprendre la sortie de `rewritemeta` sur ce point** : quelle que
   soit la version installée ici, elle se trompe — l'ancienne laissait la
   valeur sur une seule ligne, et la 2.4.5 défait activement le repli qu'on
   vient de poser. C'est leur forme canonique qui décide, pas la nôtre. Le
   `lint`, lui, n'a rien à redire au repli : il passe en silence sur la recette
   telle qu'elle est ici.
4. Ouvrir la merge request, et **mentionner la RFP #4244** dedans pour que les
   deux se rejoignent.

## Les choix qui demanderaient une explication à un relecteur

- **`subdir: zyroom-android/app`** — le dépôt porte deux applications, la GTK
  et l'Android. Gradle retrouve seul le projet racine en remontant d'un cran,
  jusqu'à `zyroom-android/settings.gradle.kts`.
- **`gradle: [fdroid]`** — trois variantes partagent le code. Celle-ci est la
  variante des joueurs débarrassée de ce que les règles de F-Droid refusent :
  elle ne va pas chercher ses mises à jour toute seule, et elle n'embarque pas
  le `string_client.pack` du jeu.
- **Pas de `scandelete`**, et c'est le piège qui a coûté un premier pipeline
  rouge. La recette en portait deux lignes, pour écarter `packAssets` et
  `packRes` — les données et les images tirées du jeu — en croyant que leur
  analyseur buterait dessus. Il n'en a rien trouvé à dire. Or `scandelete` ne
  veut pas dire « efface ces dossiers » : il veut dire « si l'analyse **objecte**
  à un fichier de ce chemin, efface-le au lieu d'échouer ». Une entrée dont
  l'analyse n'a jamais eu besoin est comptée comme une **erreur** — « Unused
  scandelete path » — et la construction s'arrête là. Les deux lignes sont donc
  retirées, et rien ne manque : la variante `fdroid` ne compile ni l'un ni
  l'autre de ces dossiers, l'APK reste propre.
- **`UpdateCheckMode: HTTP` et non `Tags`** — c'est le point le moins évident.
  Les numéros de version ne sont pas écrits en clair dans `build.gradle.kts` :
  ils viennent de `version.properties`, que `livraison.sh` fait croître, et
  l'analyseur de F-Droid ne sait pas les y lire. En revanche le `version.json`
  publié sur la page les porte tels quels, et c'est ce que la ligne
  `UpdateCheckData` va chercher. Le motif est ancré sur la clé
  `net.ryzom.zyroom` pour ne pas attraper celle de la variante dev, qui la
  suit dans le même fichier.
- **`AutoUpdateMode: Version v%v`** — chaque livraison des joueurs porte une
  étiquette git `v<numéro>` : `v2.3`, `v2.28`… C'est là que F-Droid ira
  chercher le code d'une version qu'il aura vue passer.

  Ce qui suppose que l'étiquette existe, et elle a bien failli manquer :
  l'étiquetage se faisait de tête et s'était arrêté à `v2.32`, quand
  l'application en était à 2.38. Les quarante-quatre manquantes ont été posées
  après coup, et `livraison.sh` affiche désormais la commande, numéros déjà
  remplis, dans son pense-bête de fin.

## Ce qui reste à faire avant que la fiche soit présentable

Les **captures d'écran** sont là — quatre par langue, `fr-FR` et `en-US`, dans
`fastlane/metadata/android/*/images/phoneScreenshots/`. C'était l'objet même de
la remarque du robot, et le seul manque qui aurait fait sortir la fiche nue.

Restent deux choses :

- Les **notes de version manquent pour les versionCode 43 et 44**, dans
  `fastlane/metadata/android/*/changelogs/`. La série s'arrête à 42. F-Droid
  affiche la note du versionCode qu'il publie : sans `44.txt`, la fiche
  annonce la version courante sans dire ce qu'elle apporte. (Le 38 manque
  aussi, mais celui-là n'a jamais été livré — la numérotation saute quand elle
  repart du numéro publié.)
- La description de la RFP annonce **GPL-3.0-or-later** alors que le projet
  est sous **AGPL-3.0-or-later** — c'est la seconde qui est vraie, et c'est
  elle qui est dans la recette. La demande gagnerait à être corrigée.
