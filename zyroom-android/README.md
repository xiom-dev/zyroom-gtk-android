# V-RyLune — Android

Vos inventaires Ryzom et les coffres de la guilde, hors du jeu. Kotlin et
Jetpack Compose.

L'application s'appelait ZyRoom Android jusqu'au 9 août 2026 ; elle porte
désormais le nom de la guilde à qui elle est destinée. **L'identifiant de
paquet, lui, ne change pas** et reste `net.ryzom.zyroom` : Android reconnaît
une application à cet identifiant et à rien d'autre. Le modifier ferait de la
nouvelle version une application différente — les joueurs se retrouveraient
avec les deux côte à côte, sans jamais voir de mise à jour.

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
| `data/OutpostStore.kt` | le journal des prises et pertes d'avant-postes, déduit de la même façon |
| `ui/` | liste des entités, grille d'un inventaire, journal, compétences, avant-postes, détail d'un item |
| `ui/About.kt` | l'auteur, la filiation et les avis que l'AGPL demande à l'interface de porter |
| `ui/Theme.kt` | les teintes du logo, et le lettrage du titre |

Le titre est composé en **Pirata One**, et son V initial en **Cinzel
Decorative** — la gothique dessine un V qui se lit comme un U. Les deux polices
sont libres sous SIL Open Font License 1.1. Cette licence veut que son texte et sa mention de droits voyagent avec la
police : leur texte est donc à la fois dans `licenses/` et embarqué dans
l'APK (`app/src/main/assets/`), et l'écran d'information les cite. « Pirata »
et « Cinzel » sont des *Reserved Font Names* — les fichiers ne doivent pas être
renommés pour désigner une version modifiée.

La couleur du vert vit à deux endroits, faute de mieux : `Theme.kt` pour
l'interface, et `res/values/colors.xml` pour la barre de navigation du système,
que le thème XML peint avant que Compose ne s'exécute.

## Deux variantes

Le même code donne deux applications. Elles portent des identifiants distincts
et s'installent donc **côte à côte** sur le même téléphone : celle des joueurs
et celle du mainteneur, qui essuie les plâtres.

| variante | identifiant | nom au lanceur | petit coffre | se met à jour seule |
|---|---|---|---|---|
| `guilde` | `net.ryzom.zyroom` | V-RyLune | présent, mais **vide** | oui, depuis la page GitHub |
| `dev` | `net.ryzom.zyroom.dev` | V-RyLune (dev) 2.0 | montré | oui |

```
./gradlew assembleGuildeRelease   # app/build/outputs/apk/guilde/release/
./gradlew assembleDevRelease      # app/build/outputs/apk/dev/release/
```

Une troisième variante a existé, `fdroid` : la même que `guilde`, débarrassée de
ce que la logithèque n'acceptait pas. La démarche a été abandonnée le 31 août
2026 et la variante avec elle — elle obligeait à écrire en trois exemplaires
toute interface propre à une diffusion, pour une publication qui n'aura pas
lieu. `git log` en garde le détail.

Le wrapper Gradle est dans le dépôt, binaire compris : un clone frais construit
sans qu'aucun Gradle soit installé, ce qui est le cas de la machine de
développement. Régénérer ce binaire demanderait justement un Gradle déjà là.

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

Ce qui les sépare tient dans deux constantes, `MASQUE_COFFRES` et
`MISES_A_JOUR_INTEGREES`, déclarées une fois par variante dans
`src/<variante>/kotlin/Diffusion.kt`. On aurait pu passer par `BuildConfig`,
mais l'activer fait générer du Java, donc appelle `javac`, qui réclame ici un
`jlink` absent du JDK installé.

Chaque variante a un test qui **fixe ces valeurs** (`src/test<Variante>/`) : les
autres tests comparent le réglage à ce que fait l'analyseur, et passeraient donc
tout aussi bien si une variante était compilée à l'envers, les deux étant alors
faux ensemble. Intervertir les fichiers fait maintenant échouer la construction
au lieu de partir masque baissé.

**Ce masque n'est pas une protection** : le contenu du coffre voyage toujours
dans le flux de l'API et dort dans le cache de l'application. Qui a la clé de la
guilde peut l'y lire.

## Les avant-postes

Le flux d'une guilde ne dit d'elle que la liste de ses avant-postes, et il faut
sa clé pour l'obtenir. `https://api.ryzom.com/guilds.php` en dit bien plus et
**ne demande aucune clé** : les 2 420 guildes du serveur, avec leur nom, leur
emblème et leurs avant-postes. C'est la seule source publique sur le sujet.

Elle ne donne que la propriété. Ni production, ni horaire d'attaque : rien de
tout cela n'est exposé. Les noms lisibles, eux, sont dans le pack livré, sous
`<code>.outpost`.

**Le niveau non plus n'est pas dans l'API**, et c'est pourtant une donnée fixe :
le wiki énonce la règle — « la qualité des produits correspond au niveau de
récolte maximal dans la région où se situe l'avant-poste ». Un avant-poste ne
change donc de niveau que si le jeu change. `model/OutpostLevels.kt` en tient la
table, tirée du classement par étoiles de `fr.wiki.ryzom.com/wiki/Avant-postes`
— une étoile pour cinquante niveaux — et recoupée avec `mymap.ryzom.eu.org` :
vingt-sept valeurs communes, aucun désaccord. Les quatre `primes_outpost_*`,
que le pack annonce « en test, instable », n'y figurent pas et s'affichent avec
un tiret plutôt qu'un niveau inventé.

À refaire si le jeu ajoute des avant-postes : c'est la seule partie de
l'application qui vieillit toute seule.

Le document pèse un demi-méga-octet et le serveur ne le compresse pas — moitié
moins tout de même que le flux de guilde que l'application télécharge déjà. Ce
qui compte est la fréquence, pas le poids : il n'est demandé qu'à l'ouverture de
l'onglet, et gardé une heure.

Le journal des prises et des pertes suit le même principe que celui des
mouvements, et pour la même raison : l'API ne rend qu'un état. Deux relevés
comparés donnent les changements de main ; au tout premier, il n'y a rien à
comparer et l'écran le dit, plutôt que de laisser croire à un calme plat.

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

## Filtrer

La recherche ne répond qu'à une question : où est *cet* objet. Les autres — ce
qui est monté en sève, ce qui reste en armure lourde au-dessus de la qualité
200, ce qu'on a mis en vente — se posent par élimination, au bouton
**Filtres**, au bout de la rangée des tris.

Neuf critères, les mêmes que sur le bureau : les quatre bonus de craft, une
plage de qualité, trois interrupteurs (cadenas, avec bonus, en vente) et quatre
groupes — type d'objet, classe, écosystème, emplacement d'équipement.

Trois choses valent d'être sues avant de s'en servir :

- **Les quatre bonus ne se lisent pas comme les autres groupes.** Tous cochés,
  ils ne trient rien, objets sans bonus compris : c'est l'état de repos, pas
  une demande. Dès qu'une case tombe, ne restent que les objets portant l'un
  des bonus encore cochés — décocher trois cases sur quatre, c'est demander
  « montre-moi ce qui est monté en sève », pas « montre-moi tout sauf ».
- **L'emplacement ne qualifie que l'équipement.** Une matière n'en a pas, et
  décocher toute la rangée ne la fait pas disparaître.
- **Les filtres survivent au changement de coffre**, comme le tri : on cherche
  à travers les coffres, et les reposer à chaque fois reviendrait à ne pas les
  avoir. Le bouton porte une pastille tant qu'un critère retire quelque chose —
  sans quoi une grille à moitié vide n'aurait pas d'explication visible.

Le calcul vit dans `model/Filtres.kt`, sans un mot de Compose : c'est la seule
part où l'on se trompe, et un critère qui retire un objet de trop ne se voit
pas — le coffre paraît simplement plus vide qu'il n'est. `FiltresTest` le
tient.

Trois des critères demandent ce que le flux ne dit pas. La classe se lit dans
l'énergie pour un objet crafté, dans le nom de fiche pour une matière — c'est
le nom qui l'emporte quand il a parlé, comme sur le bureau. L'écosystème et
l'emplacement se déduisent eux aussi du nom, au fil de l'analyse que `Volume`
faisait déjà pour l'encombrement : elle les traversait sans les retenir.

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

Pas de parenthèses dans les noms de fichiers : ils finissent dans une URL et
dans une ligne de commande, où elles se font réécrire ou avaler. La règle vient
des pièces jointes des Releases, que GitHub renommait en points — on ne publie
plus ainsi, l'APK est servi par la page sous un nom fixe, mais la règle reste
bonne.

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
