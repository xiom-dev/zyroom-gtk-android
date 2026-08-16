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
3. Vérifier la mise en forme avec leurs outils, si on les a :
   `fdroid readmeta && fdroid lint net.ryzom.zyroom && fdroid rewritemeta net.ryzom.zyroom`
   (`rewritemeta` remet le fichier dans leur ordre canonique — ne pas s'étonner
   qu'il déplace des lignes.)
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
- **`scandelete`** — les deux dossiers effacés (`packAssets`, `packRes`)
  contiennent des données et des images tirées du jeu, dont la licence n'est
  pas établie. La variante `fdroid` ne les compile pas ; on les retire donc
  aussi de l'arbre avant l'analyse, plutôt que de laisser le scanner buter
  dessus.
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

## Ce qui reste à faire avant que la fiche soit présentable

Les **captures d'écran** manquent dans
`fastlane/metadata/android/*/images/phoneScreenshots/`. C'était l'objet même de
la remarque du robot : sans elles, la fiche F-Droid sort nue. À prendre sur la
variante `fdroid`, qui ne porte pas la pastille « DEV ».

Et la description de la RFP annonce **GPL-3.0-or-later** alors que le projet
est sous **AGPL-3.0-or-later** — c'est la seconde qui est vraie, et c'est elle
qui est dans la recette. La demande gagnerait à être corrigée.
