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
| `ui/` | liste des entités, grille d'un inventaire, journal, détail d'un item |

## Deux variantes

Le même code donne deux applications, comme les deux bundles Flatpak du bureau.
Elles portent des identifiants distincts et s'installent donc **côte à côte** sur
le même téléphone.

| variante | identifiant | nom au lanceur | petit coffre de Nizy |
|---|---|---|---|
| `guilde` | `net.ryzom.zyroom` | ZyRoom | présent dans la liste, mais **vide** |
| `dev` | `net.ryzom.zyroom.dev` | ZyRoom (dev) | montré comme les autres |

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

Les tests de `app/src/test/` couvrent le lecteur de pack et celui des flux. Deux
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
./gradlew assembleDebug   # app/build/outputs/apk/debug/app-debug.apk
./gradlew test            # les tests, sans téléphone ni émulateur
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
export ANDROID_HOME=~/Android/Sdk
./gradlew assembleGuildeRelease assembleDevRelease
cp app/build/outputs/apk/guilde/release/app-guilde-release.apk dist/ZyRoom-Android_0.3.apk
cp app/build/outputs/apk/dev/release/app-dev-release.apk "dist/ZyRoom-Android(dev)_0.3.apk"
```

`versionName` et `versionCode` ne bougent pas d'une livraison à l'autre : c'est
le nom du fichier qui porte le numéro. Android accepte de réinstaller par-dessus
à `versionCode` égal, mais refusera un jour une vraie mise à jour si on veut
passer par un magasin — le passer à 2 est une décision à prendre.

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
