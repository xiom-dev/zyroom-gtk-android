# Métadonnées de logithèque

Ce que F-Droid lit dans le dépôt pour composer la fiche de l'application :
titre, descriptions, journal des versions, images. Rien ici n'entre dans l'APK.

    metadata/android/<langue>/
        title.txt                      le nom affiché
        short_description.txt          une ligne, 80 caractères au plus
        full_description.txt           la fiche ; balises <b> <i> <ul> <li> admises
        changelogs/<versionCode>.txt   ce que change cette version
        images/icon.png                512 × 512
        images/phoneScreenshots/       1.png, 2.png… dans l'ordre d'affichage

Le nom d'un journal est un **versionCode**, pas un numéro affiché : `14.txt`
accompagne la version 2.9, dont le versionCode vaut 14. Voir `version.properties`,
que `livraison.sh` fait croître — un journal nommé d'après le numéro affiché ne
serait jamais retrouvé.

Deux langues sont tenues : `fr-FR`, celle de la guilde, et `en-US`, celle que
F-Droid montre par défaut à qui n'a ni l'une ni l'autre.

**Les captures manquent encore.** À prendre sur la variante `fdroid`, qui ne
porte pas la pastille « DEV » du coin de l'écran, et à déposer dans
`images/phoneScreenshots/`. Trois ou quatre suffisent : l'accueil, un
inventaire, l'arbre des compétences, la météo.
