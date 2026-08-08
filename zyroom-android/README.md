# ZyRoom Android

Portage de ZyRoom GTK sur téléphone, en Kotlin et Jetpack Compose.

> Licence **GNU AGPLv3**, comme le zyRoom d'origine de Misugi
> (https://github.com/misugi/zyroom) dont ce portage dérive. Le texte complet
> est dans `LICENSE.md`. Concrètement : quiconque reçoit l'application a droit
> au code source correspondant, sous la même licence.

La logique vient de la version GTK, qui sert de spécification : le client de
l'API Ryzom, la lecture des flux `character.php` et `guild.php`, le lecteur de
`string_client.pack`. L'interface, elle, est à réécrire — GTK ne tourne pas sur
Android.

## Ce qui est là

| Fichier | Rôle |
|---|---|
| `model/Item.kt` | items, inventaires, entités, couleurs — l'ordre des énumérations est celui de l'original, il part dans les URL d'icônes |
| `api/RyzomApi.kt` | URL et appels HTTP, y compris `item_icon.php` |
| `api/EntityParser.kt` | lecture des flux XML, personnages et guildes |
| `names/NameDb.kt` | noms d'items depuis `string_client.pack`, dans ses deux formats |
| `data/EntityStore.kt` | les entités suivies et leurs clés, en JSON |
| `data/Repository.kt` | va chercher, garde en cache, et n'appelle l'API que si `cached_until` est dépassé |
| `data/MovementStore.kt` | le journal : ce qui est entré et sorti des contenants, déduit de deux relevés |
| `ui/` | liste des entités, grille d'un inventaire, journal, compétences, détail d'un item |
| `ui/About.kt` | le crédit d'auteur et les avis que l'AGPL demande à l'interface de porter |
| `ui/Theme.kt` | les teintes du logo, et le lettrage du titre |

Le titre est composé en **Pirata One**, police libre sous SIL Open Font License
1.1. Cette licence veut que son texte et sa mention de droits voyagent avec la
police : il est donc à la fois dans `licenses/OFL-PirataOne.txt` et embarqué dans
l'APK (`app/src/main/assets/`), et l'écran d'information la cite. « Pirata » est
un *Reserved Font Name* — le fichier ne doit pas être renommé pour désigner une
version modifiée.

La couleur du vert vit à deux endroits, faute de mieux : `Theme.kt` pour
l'interface, et `res/values/colors.xml` pour la barre de navigation du système,
que le thème XML peint avant que Compose ne s'exécute.

## Deux variantes

Le même code donne deux applications, comme les deux bundles Flatpak du bureau.
Elles portent des identifiants distincts et s'installent donc **côte à côte** sur
le même téléphone.

| variante | identifiant | nom au lanceur | petit coffre de Nizy |
|---|---|---|---|
| `guilde` | `net.ryzom.zyroom` | ZyRoom | présent dans la liste, mais **vide** |
| `dev` | `net.ryzom.zyroom.dev` | ZyRoom (dev) 0.5 | montré comme les autres |

Le nom au lanceur de la variante dev porte son numéro : les deux applications
cohabitant sur le même téléphone, c'est le seul endroit qui dise du premier coup
d'œil quelle version d'essai est en place. Il se déduit de `version.properties`
par un `manifestPlaceholders`, donc il suit tout seul — écrit à la main, il
aurait été un troisième endroit à tenir d'accord, et faux au premier oubli.
Celui des joueurs reste nu : le bandeau de mise à jour leur dit le numéro quand
il compte.

Le coffre masqué garde sa place et son nom : le faire disparaître amenait les
joueurs à demander pourquoi il manquait un coffre. Vide, il ne pose plus de
question.

Ce qui les sépare tient dans une constante, `MASQUE_COFFRES`, déclarée une fois
par variante dans `src/guilde/kotlin/` et `src/dev/kotlin/`. On aurait pu passer
par `BuildConfig`, mais l'activer fait générer du Java, donc appelle `javac`, qui
réclame ici un `jlink` absent du JDK installé.

**Ce masque n'est pas une protection** : le contenu du coffre voyage toujours
dans le flux de l'API et dort dans le cache de l'application. Qui a la clé de la
guilde peut l'y lire.

## Le journal

L'API de Ryzom ne tient **aucun historique** : elle ne renvoie qu'un état. Les
mouvements se déduisent donc de la comparaison de deux relevés successifs, et
seul ce qui a bougé entre les deux est vu — deux mouvements qui s'annulent
entre-temps passent inaperçus. C'était déjà la limite de l'application d'origine.

Le journal s'écrit dans les fichiers privés et non dans le cache : c'est le seul
historique qui existe, vider le cache ne doit pas l'effacer. Il s'élague au-delà
de vingt mille lignes.

## Les compétences

Le flux personnage porte l'arbre entier — cent soixante-quatorze compétences sur
le personnage d'essai, en quatre branches. Une balise par compétence, nommée par
son **code** : `sf` Combat, `sfm` Mêlée, `sfms` Manier épée. Le code contient
celui de son parent, la hiérarchie n'a donc pas à être décrite ailleurs et
l'ordre alphabétique des codes est déjà celui de l'arbre.

Le niveau arrive **décimal quand la compétence monte** : `164.52` se lit niveau
164, et 52 % du suivant. Une valeur entière ne dit rien de l'avancement, l'API ne
le donne que des niveaux entamés — d'où le filtre « En cours », qui ne garde que
ceux-là.

Le niveau d'une racine plafonne bas — Combat vaut 20 : c'est le plus haut de ses
descendants qui dit où en est la branche, et c'est lui qu'on affiche en tête.

**Toute compétence qui a des descendants se plie**, pas seulement les quatre
racines : ouvrir Artisanat d'un coup déversait cent sept lignes. Une compétence
n'apparaît que si tous ses parents sont ouverts, et replier un parent n'oublie
pas l'état des échelons du dessous — le rouvrir les retrouve tels quels. Le
calcul vit dans `model/SkillTree.kt`, hors de l'écran, pour être couvert par des
tests : le parent est le plus proche des ancêtres, non la racine, sans quoi un
échelon absent du flux décalerait tout l'affichage.

Les noms français sortent du pack livré, par ces mêmes codes. Ils ne finissent
pas en `.sitem` : la règle qui ne retenait que les items les laissait tomber, et
l'écran n'aurait montré que des codes.

Le bloc peut manquer — c'est un module de l'API, et toutes les clés ne
l'accordent pas. La puce « Compétences » ne s'affiche alors pas du tout.

Les tests de `app/src/test/` couvrent le lecteur de pack et celui des flux. Trois
d'entre eux se branchent sur les vraies données du poste quand elles sont là —
le pack du client, le cache de la version GTK — et se désactivent sinon.

## Ce qui manque

Les filtres autres que la recherche.

## Construire

L'outillage est en place sur ce poste : JDK 21, SDK Android dans
`~/Android/Sdk` (plateforme 35, outils de construction 35), Gradle 8.9 dans
`~/.local/share/`. Le chemin du SDK est dans `local.properties`, hors dépôt.

```sh
export ANDROID_HOME=~/Android/Sdk
./gradlew assembleGuildeDebug   # app/build/outputs/apk/guilde/debug/app-guilde-debug.apk
./gradlew test                  # les tests, sans téléphone ni émulateur
```

Pour installer sur un téléphone branché en débogage USB :

```sh
~/Android/Sdk/platform-tools/adb install -r app/build/outputs/apk/debug/app-debug.apk
```

## Rafraîchissement

**Rien ne tourne en arrière-plan, et c'est voulu** : l'application se met à jour
à l'ouverture d'une entité et sur le bouton ⟳, pas autrement. Elle ne réveille
donc jamais le téléphone et ne coûte rien à la batterie.

Même dans ce cadre, on ne dérange pas l'API pour rien : elle sert le même
document jusqu'à la date qu'elle annonce dans `cached_until` — presque vingt
heures sur les flux observés. `Entity.isStale()` sert à cela ; le bouton ⟳,
lui, force le passage.

Les alertes suivent la même règle : elles se recalculent à chaque chargement et
s'affichent dans l'application, à la cloche. Pas de notification système, pas de
son.

## Distribuer à la guilde

L'APK de distribution est signé avec le magasin de clés de `keystore/`, décrit
par `keystore.properties` — les deux hors dépôt. **C'est cette clé qui prouve
que les mises à jour viennent de la même main** : la perdre oblige chacun à
désinstaller avant de réinstaller.

```sh
./livraison.sh dev          # variante du mainteneur, numéro d'affichage inchangé
./livraison.sh guilde 0.4   # variante des joueurs, renumérotée 0.4
./livraison.sh tout 0.4     # les deux
```

Le script construit, signe, nomme le fichier et met à jour le `version.json`
que les téléphones interrogent. Il n'envoie rien : il affiche les commandes de
publication qui restent.

**Pourquoi ne pas le faire à la main.** `versionCode` est le seul numéro
qu'Android ordonne, donc le seul que la vérification de mise à jour compare
(`UpdateChecker`). L'oublier ne casse rien de visible : l'APK se construit,
s'installe, se lance — et aucun téléphone ne verra jamais la mise à jour. Une
livraison doit tenir d'accord quatre choses : le `versionCode` compilé, le nom
du fichier, le `versionCode` publié dans `version.json` et l'URL qu'il annonce.
Le script est le seul endroit où elles sont écrites ensemble.

L'application interroge `version.json` **à chaque retour au premier plan**, pas
une fois par lancement : un téléphone garde les applications en mémoire des
jours durant, et une version publiée pendant ce temps restait invisible — il
fallait balayer l'application hors des récentes pour la voir arriver, ce à quoi
personne ne pense. `UpdateChecker` garde sa réponse une minute, une bascule
d'application ne redemande donc pas le manifeste, et un échec réseau ne fait pas
oublier ce qu'on savait déjà.

Les numéros vivent dans `version.properties`, lu par `build.gradle.kts` ; le
script les fait croître à partir du plus haut des deux — celui du dépôt et celui
réellement en ligne. Les deux variantes ont leur propre suite : la dev avance au
rythme des essais sans entraîner celle des joueurs.

Pas de parenthèses dans les noms de fichiers : GitHub les réécrit en points sur
les pièces jointes des Releases, et les empreintes publiées ne correspondent
plus aux noms servis.

Pour l'installer, un téléphone doit autoriser les applications d'origine
inconnue — Android le propose au moment de l'ouverture du fichier. L'application
ne demande que l'accès au réseau.

L'application démarre vide. Chacun ajoute **deux** clés d'API : celle de la
guilde, diffusée sur son Discord, et la sienne pour ses propres inventaires.
Rien d'autre à faire, les noms d'items sont déjà là.

La clé de la guilde n'est **pas** livrée avec l'application : elle y serait en
clair, et donnerait à tout installateur un accès en lecture à ses coffres.

## Les noms d'items

`app/src/main/assets/string_client.pack` est livré avec l'application — 2,4 Mo,
qui n'en pèsent que 0,3 une fois compressés dans l'APK. C'est le pack français
du client ; l'application restant en français, il vaut pour tout le monde.

Un pack déposé par l'utilisateur, via le bouton de l'écran d'accueil, prend le
pas sur celui-ci : c'est ainsi qu'on rattrape les items ajoutés par une mise à
jour du jeu sans republier l'application.

Sa lecture se fait toujours en tâche de fond : deux mégaoctets et demi à
parcourir figeraient l'écran une à trois secondes.
