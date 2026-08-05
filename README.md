# ZyRoom GTK

Portage **GTK4 / Python** de l'application Windows **zyRoom** (à l'origine en
Delphi, par Misugi), pour une utilisation native sous **Debian / Linux**.

Outil compagnon du MMORPG **Ryzom** : consultez hors-ligne les inventaires de vos
personnages via l'API web officielle de Ryzom.

> Licence **GNU AGPLv3** (comme le projet d'origine : https://github.com/misugi/zyroom).

## État

Fonctionnel :
- Ajout de **personnages ET guildes** via clé API (persistés localement).
- Synchronisation via `character.php` / `guild.php`, avec **cache hors-ligne**.
- Inventaires : **Sac**, **Salle**, montures/packers/zig (perso) ; **Salle** et
  **coffres** (guilde), en grille d'icônes téléchargées et mises en cache
  (téléchargement concurrent).
- **Noms d'items lisibles** via `string_client.pack` (bouton dossier), avec cache.
- **Recherche** par nom (tolérante aux accents) et **filtres** qualité min/max +
  « protégés seulement ».
- **Calcul de volume** par item et par inventaire, avec **jauge de remplissage**
  (capacités : sac 300, salle 2000, packer 500, monture 300, zig 150).
- **Alertes** : volume au-dessus d'un seuil (défaut 90 %) et **mouvements**
  d'objets entre deux synchronisations (cloche + notification).
- Info-bulle par item (nom, fiche, qualité, quantité, volume, protection).

À venir : surveillance par item (durabilité d'un équipement, quantité d'une
matière), analyse de chatlog, sauvegardes automatiques.

## Installation

### Paquet Debian / Ubuntu (recommandé pour la guilde)

```bash
sudo apt install ./ZyRoom-GTK_6.0.0_all.deb
```

`apt` installe automatiquement les dépendances (`python3-gi`, `gir1.2-gtk-4.0`).
L'application apparaît ensuite dans le menu (« ZyRoom GTK ») ou se lance avec
`zyroom-gtk`.

### Flatpak (toutes distributions)

À partir du bundle distribué :

```bash
flatpak install --user ZyRoom-GTK_6.0.0_x86_64.flatpak
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
flatpak build-bundle build-repo ZyRoom-GTK_6.0.0_x86_64.flatpak \
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
