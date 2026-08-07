# ZyRoom GTK

Portage **GTK4 / Python** de l'application Windows **zyRoom** (à l'origine en
Delphi, par Misugi), pour une utilisation native sous **Debian / Linux**.

Outil compagnon du MMORPG **Ryzom** : consultez hors-ligne les inventaires de vos
personnages via l'API web officielle de Ryzom.

> Licence **GNU AGPLv3** (comme le projet d'origine : https://github.com/misugi/zyroom).

## Ce que l'application sait faire

- **Personnages et guildes**, ajoutés par clé API et conservés localement.
- Synchronisation via `character.php` / `guild.php`, avec **cache hors-ligne** :
  les inventaires restent consultables sans réseau.
- Tous les contenants : sac, appartement, montures, mektoubs, zigs, ventes à
  l'hôtel, et les **coffres de guilde**, en grille d'icônes mises en cache.
- **Noms d'items lisibles** tirés de `string_client.pack`, avec cache.
- **Recherche** tolérante aux accents, **filtres** (qualité, type, classe,
  écosystème, équipement, protégés, avec bonus, en vente) et **tris**.
- **Volume** par item et par contenant, avec jauge de remplissage.
- **Journal des mouvements** : ce qui est entré et sorti des coffres, horodaté
  et conservé d'une session à l'autre.
- **Alertes** à la cloche : remplissage au-delà d'un seuil, mouvements,
  durabilité et quantité des objets surveillés, ventes qui expirent, changement
  de saison.
- **Détail d'un item** : caractéristiques de craft, protections, résistances,
  spécificités de matière.
- **Analyse de chatlog** avec couleurs, filtres et export.
- **Sauvegarde** du dossier `save` de Ryzom, à la demande ou à la fermeture.
- **Mise à jour intégrée** quand l'application est installée en Flatpak depuis
  le dépôt du projet.

## Deux variantes

Le même code donne deux applications, aux identifiants distincts, installables
côte à côte : celle distribuée à la guilde masque le contenu d'un coffre
réservé, celle du mainteneur (`ZYROOM_SHOW_ALL_CHESTS=1`) montre tout.

## Installation

### Paquet Debian / Ubuntu (recommandé pour la guilde)

```bash
sudo apt install ./ZyRoom-GTK_6.0.0_all.deb
```

`apt` installe automatiquement les dépendances (`python3-gi`, `gir1.2-gtk-4.0`).
L'application apparaît ensuite dans le menu (« ZyRoom-GTK-0.3 ») ou se lance avec
`zyroom-gtk`.

### Flatpak (toutes distributions)

À partir du bundle distribué :

```bash
flatpak install --user ZyRoom-GTK-0.3.flatpak
flatpak run net.ryzom.zyroomgtk
```

La notice destinée aux joueurs est dans `packaging/INSTALLATION.md`.

### Depuis les sources (développement)

Deux paquets suffisent (GTK4 + Python) :

```bash
sudo apt install python3-gi gir1.2-gtk-4.0
git clone <cette-url> zyroom-gtk
cd zyroom-gtk
python3 build_i18n.py    # compile les traductions
./run.py
```

## Construire les paquets

### Paquet Debian

```bash
bash packaging/build-deb.sh          # -> ZyRoom-GTK_6.0.0_all.deb
# (make, dpkg-deb, fakeroot requis)
```

### Flatpak

```bash
flatpak install flathub org.gnome.Platform//50 org.gnome.Sdk//50
# si la distribution ne fournit pas flatpak-builder :
flatpak install --user flathub org.flatpak.Builder

flatpak run org.flatpak.Builder --user --install --force-clean \
    --repo=build-repo build-dir packaging/net.ryzom.zyroomgtk.yml

# bundle d'un seul fichier, à distribuer
flatpak build-bundle build-repo ZyRoom-GTK-0.3.flatpak \
    net.ryzom.zyroomgtk master
```

Le bundle ne contient que l'application (environ 220 Ko) ; le socle graphique
GNOME est téléchargé depuis Flathub à la première installation.

### Vieilles machines / pas d'accélération 3D

GTK4 utilise OpenGL par défaut. En cas de rendu lent ou de plantage graphique,
forcez le rendu logiciel :

```bash
./run.py --software        # équivaut à GSK_RENDERER=cairo
```

## Utilisation

1. Cliquez sur **＋** dans la barre de titre.
2. Choisissez **Personnage** ou **Guilde**, collez la **clé API** (obtenue sur
   https://app.ryzom.com/app_ryzomapi). Modules requis : personnage
   C01/C04/C05/C06/A01/A03 ; guilde G01/G02/G03.
3. Choisissez une entité puis un inventaire pour voir les items.
4. (Optionnel) Bouton **dossier** : chargez `string_client.pack` (dossier
   d'installation de Ryzom) pour afficher les **noms d'items**.
5. Recherchez par nom et filtrez par qualité / items protégés.

Vos clés sont stockées **en clair** dans `~/.config/zyroom-gtk/characters.ini`
(chaque joueur y met la sienne). Les données mises en cache (flux XML, icônes)
sont dans `~/.cache/zyroom-gtk/`.

## Architecture

| Module | Rôle |
|--------|------|
| `zyroom/models.py` | Modèle d'item + parsing d'un noeud XML (fidèle au Delphi) |
| `zyroom/ryzom_api.py` | Client API (urllib) + parsing des inventaires |
| `zyroom/sheetdb.py` | Chargement de `sheetid.csv` |
| `zyroom/icons.py` | Cache disque + téléchargement concurrent des icônes |
| `zyroom/config.py` | Chemins XDG + persistance des personnages |
| `zyroom/window.py` | Fenêtre principale GTK4 |
| `zyroom/app.py` / `run.py` | Application et point d'entrée |

Aucune dépendance hors GTK : le réseau et le XML utilisent la bibliothèque
standard de Python.
