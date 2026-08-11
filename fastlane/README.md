# Métadonnées de logithèque

**Ce dossier doit rester à la racine du dépôt.** F-Droid cherche `fastlane/` à
la racine, ou sous le répertoire du module gradle qu'il construit — jamais
ailleurs. Il a d'abord vécu dans `zyroom-android/`, où il paraissait à sa
place puisqu'il ne décrit que l'application Android ; le robot de F-Droid a
répondu « Fastlane was not found in your repo », et sans lui la fiche n'aurait
ni capture d'écran ni description modifiable sans passer par leur équipe.

Ce que F-Droid lit dans le dépôt pour composer la fiche de l'application :
titre, descriptions, journal des versions, images. Rien ici n'entre dans l'APK.

    metadata/android/<langue>/
        title.txt                      le nom affiché
        short_description.txt          une ligne, 80 caractères au plus
        full_description.txt           la fiche ; balises <b> <i> <ul> <li> admises
        changelogs/<versionCode>.txt   ce que change cette version
        images/icon.png                512 × 512
        images/phoneScreenshots/       1.png, 2.png… dans l'ordre d'affichage

Le nom d'un journal est un **versionCode**, pas un numéro affiché : `19.txt`
accompagne la version 2.14, dont le versionCode vaut 19. Voir
`version.properties`, que `livraison.sh` fait croître.

Les deux se ressemblent assez pour qu'on les confonde, et la panne est
silencieuse : un journal nommé d'après le numéro affiché n'est jamais retrouvé,
la fiche sort sans note de version, et rien ne le signale. C'est arrivé ici —
le fichier a suivi le numéro affiché pendant deux versions avant qu'on s'en
aperçoive.

Deux langues sont tenues : `fr-FR`, celle de la guilde, et `en-US`, celle que
F-Droid montre par défaut à qui n'a ni l'une ni l'autre.

**Les captures manquent encore.** À prendre sur la variante `fdroid`, qui ne
porte pas la pastille « DEV » du coin de l'écran, et à déposer dans
`images/phoneScreenshots/`. Trois ou quatre suffisent : l'accueil, un
inventaire, l'arbre des compétences, la météo.
