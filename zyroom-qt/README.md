# ZyRoom-Qt

Portage **Qt/Python** du zyRoom de Misugi — l'outil compagnon du MMORPG
[Ryzom](https://ryzom.com) : consulter hors-ligne les inventaires de ses
personnages et des coffres de sa guilde, via l'API web officielle.

Troisième portage du dépôt, après [`zyroom-gtk/`](../zyroom-gtk/) (Linux) et
[`zyroom-android/`](../zyroom-android/) (téléphone). Celui-ci vise **Linux et
Windows** à partir du même code.

## État

**La mise en page est celle de ZyRoom-GTK**, reprise à l'identique : barre
d'actions et navigation en haut, bande des deux sélecteurs, ligne de volume,
ligne de recherche et de tri, grille d'objets, et en bas la bande d'état —
portrait, ligne « qui / quoi / quand », nom gravé au centre, dappers à droite,
signature dessous.

Ce qui marche de bout en bout :

- lecture de la configuration (et **reprise automatique** de celle de
  ZyRoom-GTK au premier lancement — les clés d'API ne se ressaisissent pas) ;
- ajout d'un personnage ou d'une guilde à partir d'une clé, vérifiée auprès
  de l'API avant d'être enregistrée ;
- synchronisation dans un thread, avec mise en cache du flux XML ;
- affichage hors-ligne immédiat depuis ce cache ;
- contenants, jauge de volume, grille d'objets avec icônes téléchargées en
  parallèle et gouttes de bonus peintes dessus, infobulles ;
- recherche, panneau de filtres complet et tri réglable, mémorisé ;
- portrait recadré, dappers, message du jour de guilde, saison d'Atys ;
- **fiche détaillée d'un objet** (double-clic, ou clic droit → Détails) avec
  ses huit sections de caractéristiques ; le clic droit copie aussi
  l'identifiant et réinitialise l'icône ;
- **journal des mouvements** : ce qui est entré et sorti à chaque relevé, daté,
  avec recherche, filtre entrées/sorties, copie et vidage. Les instantanés et
  l'historique de ZyRoom-GTK sont repris au premier lancement — c'est la seule
  donnée que l'API ne sait pas reconstruire ;
- **options** complètes (langue, chemins du jeu, seuils, notifications,
  intervalle de relevé, sauvegarde, proxy) ;
- **gestion des clés** à deux onglets : en ajouter une, relire celles qu'on a,
  les copier, les remplacer, retirer une entité ;
- **chargement du `string_client.pack`** et **À propos** portant les mentions
  que l'AGPL exige ;
- **resynchronisation périodique** : toutes les entités suivies, pas seulement
  celle qu'on regarde — sinon les autres journaux auraient des trous ;
- les cinq écrans du menu « Bonus » :
  - **Compétences** — l'arbre à quatre branches, pliable à tous les échelons,
    avec niveaux, avancement et points par branche ;
  - **Effectif** — les membres par grade sur six colonnes, et le journal des
    arrivées, départs et changements de grade ;
  - **Avant-postes** — qui tient quoi sur Atys, par peuple, avec les emblèmes
    de guilde et le journal des prises ;
  - **« Perdu ? »** — où sont vos montures, sur la carte d'Atys, avec zoom à
    la molette, glissement à la souris et regroupement des bêtes voisines ;
  - **Météo** — la courbe de l'humidité en paliers, ses seuils, les nuits
    d'Atys et le trait du présent qui glisse comme un sismographe ; puis ce qui
    sort maintenant dans les quatre zones des Primes, et les excellentes de la
    saison.

  Les trois premiers s'ouvrent **quelle que soit l'entité choisie** : ils
  reprennent la dernière guilde et le dernier personnage rencontrés. Consulter
  un effectif ne devrait pas obliger à changer d'entité.

- les **cartes de gisements** : dans l'écran Météo, cliquer une matière ouvre
  la carte de ses points connus, cadrée automatiquement dessus, avec le nom de
  chaque lieu. Une matière qu'on ne sait pas situer reste du texte ordinaire —
  rien n'invite à cliquer sur ce qui ne répondrait pas.

- les **alertes et la surveillance** : la cloche et son panneau, les seuils
  posés sur un objet (quantité ou durabilité, par clic droit), la surveillance
  du trésor, et les bulles près de l'horloge.

- l'**analyse d'un chatlog** : filtre par canal et par mot, messages aux
  couleurs du jeu, export en HTML, BBCode ou texte ;
- la **sauvegarde** du dossier « save » de Ryzom, à la demande.

- la **mise à jour intégrée**, réinventée : voir plus bas.

Et les détails qui font qu'on reconnaît l'application : l'icône du sort gravé
posée sur celle d'un objet enchanté, les gouttes de bonus dessinées **dans**
l'infobulle et non décrites en mots, les journaux de guilde publiés par la
page versés dans les siens au lancement, la saison d'Atys qui avance toute
seule entre deux relevés.

**Le portage est fonctionnellement complet.** Tout ce que fait ZyRoom-GTK se
fait ici.

## Ce qui reste à faire, et qui n'est plus du code

**Le faire essayer par un joueur sous Windows.** Chaque étiquette `qt-*` fait
construire les deux paquets Windows — le public et celui du chef — par GitHub
Actions, sur une vraie machine Windows, diagnostic compris ; ce sont eux qui
sont servis, et `outils/publier-windows.sh` va les chercher sans qu'on ouvre
le navigateur. Mais un diagnostic qui passe n'est pas une partie jouée :
personne n'a encore ouvert un coffre depuis un vrai Windows.

## L'archive du chef de guilde

La variante du chef lève le masque sur le petit coffre de Nizy. Elle **ne doit
pas se trouver sur la page que les joueurs consultent** : elle vit dans un
dossier à part, avec sa propre page,

    pages/chef-98a7c4153088/

servi sur https://xiom-dev.github.io/zyroom-gtk-android/chef-98a7c4153088/ — adresse que
rien ne référence et qu'aucun lien ne donne. `index.html` de la racine ne la
mentionne pas, et la page du chef porte un `noindex`.

**Ce n'est pas un secret, c'est une adresse difficile à trouver.** Le dépôt est
public : qui parcourt la branche `gh-pages` sur GitHub voit ce dossier comme le
reste. Ce que le nom tiré au hasard empêche, c'est qu'un joueur tombe dessus en
essayant l'adresse évidente, ou qu'un moteur l'indexe. Pour davantage, il
faudrait ne pas publier l'archive du tout et la remettre au chef en main
propre.

**Elle se dépose avec l'autre.** `outils/publier-windows.sh` sort les deux
archives de l'artefact : la publique à la racine de `pages/`, celle du chef
dans son dossier sous le nom fixe que sa page appelle, plus une copie dans
`dist/`. Le script vérifie au passage qu'elle porte bien
`ZyRoom-Qt-dev.bat` — sans ce lanceur, c'est l'archive publique qu'on
s'apprêterait à servir sous le nom du chef, et cela ne se verrait que le jour
où il ouvrirait le petit coffre.

Elle ne se télécharge **qu'une fois** : depuis la version 1.11, la mise à jour
reporte les lanceurs trouvés en place, et `ZyRoom-Qt-dev.bat` survit donc aux
livraisons suivantes.

## Traductions

`build_i18n.py` **reprend le catalogue de ZyRoom-GTK** et le complète des
chaînes propres à ce portage — on ne retraduit pas ce qui l'est déjà, et les
deux interfaces en partagent beaucoup. Il écrit directement les `.mo` ; c'est
pourquoi `zyroom/locale/` ne fait **pas** partie de ce que
`outils/sync-noyau.sh` recopie : ce serait effacer ce travail à chaque
synchronisation.

```bash
python3 build_i18n.py
```

Deux chaînes restent en français quelle que soit la langue : le nom de la
saison et la formule « synchro aujourd'hui à… ». C'est assumé, et ZyRoom-GTK
est dans le même cas.

## La mise à jour

Le mécanisme de ZyRoom-GTK ne se réutilise pas : là-bas, l'application est en
bac à sable et passe par le portail Flatpak, en D-Bus, qui n'existe ni hors
bac à sable ni sous Windows.

Le mécanisme retenu est **celui du portage Android**, qui a le même problème :
un `version.json` publié sur la page de téléchargement annonce le dernier
`versionCode` et l'adresse de l'archive. C'est un entier qu'on compare, jamais
un nom — « 0.10 » vient après « 0.9 » pour nous, avant pour un tri de chaînes.

**Le remplacement se fait par renommage.** Un programme ne peut pas effacer le
dossier depuis lequel il tourne — sous Windows, ses fichiers ouverts sont
verrouillés. Mais le *renommer* est permis sur les deux systèmes, et c'est le
tour de main qu'emploient les navigateurs :

1. l'archive est téléchargée, puis extraite à côté de l'installation ;
2. l'installation en place est **renommée**, pas effacée ;
3. la nouvelle prend son nom ;
4. l'ancienne est effacée au lancement suivant, quand plus rien ne la tient.

Si quoi que ce soit échoue en route, l'ancienne est remise à sa place : à
aucun moment il n'existe d'état où l'application aurait disparu. Vérifié —
archive illisible, archive étrangère, absence d'installation : les trois
laissent le dossier intact.

### Pour publier une version

```bash
./livraison.sh          # construit le numéro actuel
./livraison.sh 1.12     # renumérote en 1.12, puis construit
```

Le script recopie le numéro là où il s'affiche, incrémente le `versionCode`,
vérifie que le noyau n'est pas périmé, construit le paquet Linux, le pose dans
`pages/` et remplit sa case de `version.json`. **Rien n'est envoyé sur
GitHub** : il s'arrête au bord et affiche ce qui reste à faire — pousser
`main` avec l'étiquette **annotée** `qt-<numéro>`, qui est ce qui déclenche la
construction Windows ; publier `pages/` sur `gh-pages` ; puis, la CI finie,
`outils/publier-windows.sh` et une seconde publication du site.

L'entrée du manifeste tient **une case par système**, et chaque paquet ne
compare que la sienne : Windows reste donc à sa version le temps que la CI
finisse, sans que cela dérange personne.

```json
"net.ryzom.zyroomqt": {
  "versionCode": 105,
  "versionName": "1.11.76",
  "urls": {
    "linux": "https://xiom-dev.github.io/zyroom-gtk-android/ZyRoom-Qt-linux.zip",
    "windows": "https://xiom-dev.github.io/zyroom-gtk-android/ZyRoom-Qt-windows.zip"
  },
  "systemes": {
    "linux":   { "versionCode": 105, "versionName": "1.11.76" },
    "windows": { "versionCode": 105, "versionName": "1.11.76" }
  }
}
```

`versionCode` doit croître d'une livraison à l'autre et correspondre au
`__version_code__` de `zyroom/__init__.py` : c'est lui, et lui seul, que
l'application compare. L'archive doit être en ligne **avant** que le manifeste
l'annonce, sinon le bouton mène à une adresse morte.

### Deux écarts assumés avec la version GTK

**La barre du haut n'est pas la barre de titre.** GTK4 dessine lui-même la
décoration de la fenêtre et y loge des boutons ; Qt laisse cela au
gestionnaire de fenêtres. La lui reprendre demanderait une fenêtre sans cadre,
donc de redessiner à la main déplacement, redimensionnement et boutons
système — différemment sous Linux et sous Windows. On garde la décoration
native, et une bande juste dessous porte le même contenu, dans le même ordre.

**Les gouttes de bonus sont peintes dans l'icône**, au lieu d'être posées
par-dessus dans un `Gtk.Overlay`. Une case de grille redevient un seul objet
là où il en fallait trois superposés — et une grille de coffre en compte
quatre cents.

## Le noyau est partagé, pas recopié à la main

Les modules qui parlent à l'API, analysent le XML, calculent les volumes et
tiennent les journaux sont **les mêmes fichiers** que dans `zyroom-gtk/` : ils
ne dépendent d'aucune boîte à outils graphique.

> **Règle du portage : le noyau ne s'édite QUE dans `zyroom-gtk/`.**
> Les fichiers listés dans `outils/sync-noyau.sh` sont des copies. Une
> modification faite ici sera écrasée sans avertissement.

```bash
outils/sync-noyau.sh            # recopie depuis zyroom-gtk
outils/sync-noyau.sh --verifie  # dit seulement ce qui differe
```

Trois modules échappent à la règle, parce qu'ils touchent au système ou à
l'affichage, et diffèrent donc réellement d'un portage à l'autre :

| module | pourquoi il diverge |
|---|---|
| `config.py` | XDG sous Linux, `%APPDATA%` sous Windows |
| `polices/__init__.py` | GTK passait par fontconfig en `ctypes` ; Qt charge le fichier directement |
| `icones.py` | `GLib.idle_add` d'un côté, un signal Qt en `QueuedConnection` de l'autre |
| `specialites.py` | même logique de part et d'autre, mais sa moitié basse dessine — et le dessin ne se partage pas entre Cairo et QPainter |
| `detail.py` | mêmes sections et mêmes libellés, widgets Qt |
| `notifications.py` | `Gio.Notification` sur D-Bus d'un côté ; une icône de zone de notification de l'autre, seul chemin commun à Linux et Windows |
| `chatlog.py` | analyse et exports identiques ; seule la fenêtre change |
| `options.py` | mêmes réglages dans le même ordre, widgets Qt |

## Lancer depuis les sources

PySide6 n'est pas dans les dépôts sous une forme utilisable partout, et le
Python système est protégé (PEP 668) : on passe par un environnement virtuel,
ce qui est de toute façon ce qu'il faudra sous Windows.

```bash
python3 -m venv .venv
.venv/bin/pip install PySide6-Essentials
.venv/bin/python run.py
```

Sur une machine sans accélération 3D fiable : `.venv/bin/python run.py --software`.

Pour savoir ce que l'application voit de son installation — chemins, données
embarquées, entités configurées — sans ouvrir de fenêtre :

```bash
.venv/bin/python run.py --diagnostic
```

## Construire un paquet autonome

```bash
.venv/bin/pip install pyinstaller
packaging/build.sh          # Linux
packaging\build.bat         # Windows
```

Le résultat est dans `dist/` : un dossier prêt à copier et une archive. Environ
150 Mo décompressés — c'est Qt, et `packaging/zyroom-qt.spec` écarte déjà le
moteur QML, la 3D et le multimédia.

`packaging/INSTALLATION.md` détaille l'installation, l'intégration au menu du
bureau, l'avertissement SmartScreen sous Windows et l'emplacement des données.

### Le paquet Windows

Deux façons de l'obtenir, et elles ne se valent pas.

**La bonne : GitHub Actions.** `.github/workflows/zyroom-qt-windows.yml`
construit sur une machine Windows prêtée par GitHub, se déclenche à la main
depuis l'onglet Actions ou sur une étiquette `qt-*`, et dépose l'archive en
artefact. C'est celle qui fait foi.

**La rapide : Wine.** `packaging/build-windows-wine.sh` monte un préfixe Wine
dédié — il ne touche pas à votre `~/.wine` —, y installe Python et PySide6
pour Windows, et construit. Le paquet démarre, son diagnostic est bon, ses
chemins `%APPDATA%` sont justes. Mais ce qui en sort **n'a jamais tourné sur
un vrai Windows** : Wine est une réimplémentation, et ce qu'il laisse passer
n'est pas toujours ce que Windows accepte.

> **Wine ne fournit pas ICU, et Qt6 en dépend.** Windows 10 et 11 embarquent
> `icuuc.dll` dans System32 ; PySide6 compte dessus et ne l'emporte pas dans
> sa roue. Sous Wine, l'import de `QtCore` échoue donc sur un laconique
> « Module introuvable ». Le script va chercher ICU4C et le pose dans le
> préfixe, sous ses deux noms — celui que Qt demande et celui qu'ICU se donne
> à lui-même, car le premier réclame le second. Le paquet produit, lui,
> n'embarque aucune de ces DLL : sur un vrai Windows elles viennent du
> système, et `find dist -iname 'icu*.dll'` ne rend rien.

## Les essais

```bash
python3 -m unittest discover -s tests
```

Ils tournent aussi **à chaque poussée**, par le workflow `essais.yml`, avec
ceux de ZyRoom-GTK.

Rien n'y demande PySide6, ni fenêtre, ni réseau : les essais relisent les
fichiers ou travaillent dans un dossier jetable. Ils tournent donc là où l'on
veut justement savoir si le code se tient — une machine sans l'environnement
complet, la CI, un paquet qu'on vient de sortir.

**Ce qui est couvert ici, c'est ce qui est propre au portage.** Le noyau ne
l'est pas, et n'a pas à l'être : ce sont les mêmes fichiers que ZyRoom-GTK,
dont les 326 essais valent donc pour les deux — et `sync-noyau.sh
--verifie`, appelé par les deux livraisons, dit si une copie a dérivé.

| Fichier | Ce qu'il tient |
|---------|----------------|
| `test_updater_installation.py` | Le remplacement d'un dossier d'application par le suivant : le tour de main du renommage, les liens symboliques de Qt, le bit d'exécution, le lanceur du chef, et les échecs — archive illisible, archive étrangère, pas d'installation — qui doivent tous laisser le dossier intact |
| `test_updater_manifeste.py` | La lecture du manifeste : la case par système, l'entier qu'on compare (jamais un nom), l'archive par système, et le silence en cas de panne de réseau |
| `test_updater_suffixes.py` | Les noms de dossier qui ne s'empilent pas, et le relais de Windows |
| `test_config_chemins.py` | `%APPDATA%` et `%LOCALAPPDATA%` d'un côté, XDG de l'autre ; et la reprise de la configuration de ZyRoom-GTK au premier lancement, bac à sable Flatpak compris |
| `test_coherence_interface.py` | Que l'interface ne s'appelle pas elle-même avec un nom qui n'existe plus — l'`AttributeError` du menu contextuel, qui a déjà traversé une livraison |

**Windows ne s'exécute pas ici.** Ce qui peut l'être se simule — le drapeau
`WINDOWS` et les variables d'environnement suffisent à emprunter ce
chemin-là — et le reste tient à la machine que GitHub prête.

## Licence

**GNU AGPLv3 ou ultérieure** (`AGPL-3.0-or-later`), comme le zyRoom d'origine
dont ce portage dérive — https://github.com/misugi/zyroom. Le texte complet est
dans [`LICENSE.md`](LICENSE.md).
