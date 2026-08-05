# ZyRoom GTK — installation sous Linux

Consultez vos inventaires Ryzom hors du jeu : personnages, guildes, coffres,
volumes, alertes, journal de conversation.

Deux formats sont fournis, au choix.

| Vous êtes sous… | Prenez | Pourquoi |
|---|---|---|
| **Debian, Ubuntu, Mint** | `ZyRoom-GTK_6.0.0_all.deb` | le plus léger : 190 Ko, rien d'autre à télécharger |
| **toute autre distribution** | `ZyRoom-GTK_6.0.0_x86_64.flatpak` | fonctionne partout, sans rien compiler |

---

# A. Paquet Debian / Ubuntu

```sh
sudo apt install ./ZyRoom-GTK_6.0.0_all.deb
```

`apt` installe au passage les deux dépendances nécessaires (`python3-gi` et
`gir1.2-gtk-4.0`). L'application apparaît ensuite dans le menu sous « ZyRoom
GTK », ou se lance par la commande `zyroom-gtk`.

Vos réglages vont dans `~/.config/zyroom-gtk/`, vos caches dans
`~/.cache/zyroom-gtk/`.

Pour désinstaller : `sudo apt remove zyroom-gtk`.

> **Réinstaller une version corrigée.** Le numéro de version reste 6.0.0 d'une
> livraison à l'autre. Si `apt` répond que le paquet est déjà à jour alors que
> vous venez d'en recevoir une nouvelle copie, forcez la mise en place :
> `sudo apt install --reinstall ./ZyRoom-GTK_6.0.0_all.deb`

---

# B. Flatpak (toutes distributions)

## 1. Vérifier que Flatpak est présent

```sh
flatpak --version
```

Si la commande n'existe pas, installez-le :

| Distribution | Commande |
|---|---|
| Debian, Ubuntu, Mint | `sudo apt install flatpak` |
| Fedora | `sudo dnf install flatpak` |
| Arch, Manjaro | `sudo pacman -S flatpak` |
| openSUSE | `sudo zypper install flatpak` |

Puis ajoutez le dépôt Flathub, d'où viendra la bibliothèque graphique :

```sh
flatpak remote-add --if-not-exists --user flathub https://dl.flathub.org/repo/flathub.flatpakrepo
```

## 2. Installer ZyRoom GTK

Placez-vous dans le dossier où se trouve le fichier, puis :

```sh
flatpak install --user ZyRoom-GTK_6.0.0_x86_64.flatpak
```

L'application elle-même ne pèse que 1 Mo. En revanche, si vous n'avez encore
aucune application Flatpak, Flatpak téléchargera aussi son socle graphique
(**GNOME 50, environ 1 Go**) — une seule fois, et partagé ensuite avec toutes
vos autres applications Flatpak. Prévoyez quelques minutes.

Redémarrez votre session pour voir ZyRoom GTK apparaître dans le menu des
applications.

## 3. Lancer

Depuis le menu de votre bureau, ou en ligne de commande :

```sh
flatpak run net.ryzom.zyroomgtk
```

Sur une machine ancienne ou une carte graphique capricieuse, forcez le rendu
logiciel :

```sh
flatpak run --env=GSK_RENDERER=cairo net.ryzom.zyroomgtk
```

## 4. Premier démarrage

**La guilde La Lune Eternelle est déjà configurée** : à la première ouverture,
ses coffres s'affichent sans rien avoir à saisir.

Pour voir aussi vos propres sacs et votre appartement :

1. Cliquez sur **+** puis choisissez **Personnage**.
2. Renseignez votre **clé d'API**.

Pour obtenir votre clé : connectez-vous sur https://api.ryzom.com, créez une clé
pour votre personnage en cochant au minimum les modules `C01 C04 C05 C06 A01 A03`
(pour une guilde : `G01 G02 G03`).

Votre clé reste sur votre machine : l'application ne communique qu'avec l'API
officielle de Ryzom.

> **À usage interne.** Ce paquet contient la clé de lecture de la guilde. Elle
> ne donne accès qu'à la consultation des coffres, mais quiconque reçoit le
> fichier peut s'en servir : à ne transmettre qu'aux membres.

### Fraîcheur des données

L'application interroge l'API de Ryzom à l'ouverture de chaque personnage ou
guilde, puis **toutes les quinze minutes**. La barre du bas indique la date de
la dernière synchronisation — « synchro aujourd'hui à 20h10 » — de sorte qu'un
inventaire ancien ne passe jamais pour un inventaire à jour. Le bouton **↻**
force une mise à jour immédiate.

Hors connexion, les derniers inventaires reçus restent consultables ; la date
affichée indique alors de quand ils datent.

L'intervalle se règle dans **Options** (0 pour désactiver), tout comme la
synchronisation à l'ouverture.

### Noms d'objets lisibles

Pour afficher « Ambre suprême » plutôt qu'un identifiant, l'application a besoin
du fichier `string_client.pack` fourni avec le jeu. Elle le cherche seule ; si
elle ne le trouve pas, indiquez-le avec le bouton dossier de la barre de titre.
Il se trouve dans le répertoire d'installation de Ryzom, généralement sous
`data/`.

## 5. Où sont mes données

Une application Flatpak range ses fichiers à part :

```
~/.var/app/net.ryzom.zyroomgtk/config/zyroom-gtk/   clés, réglages, alertes
~/.var/app/net.ryzom.zyroomgtk/cache/zyroom-gtk/    inventaires hors-ligne, icônes
~/.var/app/net.ryzom.zyroomgtk/data/zyroom-gtk/     sauvegardes du dossier « save »
```

Si vous utilisiez déjà ZyRoom GTK installé autrement, vos réglages ne sont pas
repris automatiquement — l'application s'ouvrira sans aucun personnage. Pour
récupérer votre configuration existante, application fermée :

```sh
mkdir -p ~/.var/app/net.ryzom.zyroomgtk/config/zyroom-gtk
cp -r ~/.config/zyroom-gtk/. ~/.var/app/net.ryzom.zyroomgtk/config/zyroom-gtk/
```

Pour reprendre aussi les icônes déjà téléchargées, et éviter de tout recharger :

```sh
mkdir -p ~/.var/app/net.ryzom.zyroomgtk/cache/zyroom-gtk
cp -r ~/.cache/zyroom-gtk/. ~/.var/app/net.ryzom.zyroomgtk/cache/zyroom-gtk/
```

## 6. Désinstaller

```sh
flatpak uninstall --user net.ryzom.zyroomgtk
```

Pour effacer aussi vos réglages et vos caches, ajoutez `--delete-data`.

## Licence

ZyRoom GTK est un logiciel libre sous **AGPL-3.0-or-later**, d'après le zyRoom
original de **Misugi**. Vous pouvez le partager et le modifier librement, à
condition de transmettre le code source avec le programme et de conserver la
même licence. Le code source accompagne ce fichier.
