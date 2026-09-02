# Installer ZyRoom-Qt

Trois façons, selon ce qu'on veut : lancer depuis les sources, construire un
paquet autonome, ou installer celui qu'on a construit.

## Depuis les sources

PySide6 n'est pas empaqueté partout sous une forme utilisable, et le Python
système de Debian est protégé (PEP 668) : on passe donc par un environnement
virtuel. C'est de toute façon ce qu'il faudra sous Windows.

```bash
python3 -m venv .venv
.venv/bin/pip install PySide6-Essentials
.venv/bin/python run.py
```

Sur une machine sans accélération 3D fiable : `run.py --software`.

## Construire un paquet autonome

Le paquet embarque Python, Qt et l'application : rien à installer sur la
machine qui le reçoit.

```bash
.venv/bin/pip install pyinstaller

# Linux
packaging/build.sh

# Windows, dans une invite de commandes
packaging\build.bat
```

Le résultat est dans `dist/` : un dossier `ZyRoom-Qt/` prêt à copier, et une
archive (`.tar.gz` sous Linux, `.zip` sous Windows).

**Un dossier plutôt qu'un exécutable unique.** Un fichier unique doit se
décompresser en entier à chaque lancement — avec Qt, une centaine de
mégaoctets et deux à trois secondes avant que la fenêtre paraisse. Le dossier
démarre aussitôt, et s'envoie tout aussi bien dans une archive.

**La taille.** Comptez environ 150 Mo décompressés : c'est Qt, et il n'y a pas
d'échappatoire — le fichier `packaging/zyroom-qt.spec` écarte déjà le moteur
QML, la 3D et le multimédia, qui pèsent le plus lourd.

## Installer le paquet construit

### Linux

```bash
tar xzf ZyRoom-Qt-*-linux-x86_64.tar.gz -C ~/.local/lib/
ln -sf ~/.local/lib/ZyRoom-Qt/ZyRoom-Qt ~/.local/bin/zyroom-qt

# Integration au menu du bureau
install -Dm644 data/net.ryzom.zyroomqt.desktop \
        ~/.local/share/applications/net.ryzom.zyroomqt.desktop
install -Dm644 data/net.ryzom.zyroomqt.svg \
        ~/.local/share/icons/hicolor/scalable/apps/net.ryzom.zyroomqt.svg
update-desktop-database ~/.local/share/applications 2>/dev/null || true
```

Tout se pose sous le répertoire personnel : rien n'est écrit hors de chez soi,
et la désinstallation se résume à effacer ces quatre chemins.

### Windows

Décompressez le `.zip` où vous voulez — `%LOCALAPPDATA%\Programs\ZyRoom-Qt`
est un choix raisonnable — puis lancez `ZyRoom-Qt.exe`. Un raccourci vers cet
exécutable, posé sur le bureau ou dans le menu Démarrer, suffit : il n'y a pas
d'installeur, et rien n'est écrit dans la base de registre.

**Ce que Windows dira au premier lancement.** L'exécutable n'est pas signé —
une signature coûte plusieurs centaines d'euros par an — et SmartScreen
affichera donc un avertissement bleu. « Informations complémentaires », puis
« Exécuter quand même ». C'est le lot de tout logiciel libre distribué hors
d'un magasin d'applications.

## Où l'application range ses affaires

| | Linux | Windows |
|---|---|---|
| Configuration, clés d'API | `~/.config/zyroom-qt/` | `%APPDATA%\zyroom-qt\` |
| Cache (icônes, flux, instantanés) | `~/.cache/zyroom-qt/` | `%LOCALAPPDATA%\zyroom-qt\cache\` |
| Journaux, sauvegardes | `~/.local/share/zyroom-qt/` | `%LOCALAPPDATA%\zyroom-qt\` |

Au tout premier lancement sous Linux, la configuration et les journaux de
ZyRoom-GTK sont **repris** s'ils existent : les clés d'API ne se ressaisissent
pas, et l'historique des mouvements — que l'API ne sait pas reconstruire — est
conservé. C'est une copie, pas un partage : les deux applications divergent
ensuite.

Désinstaller n'efface pas ces dossiers ; les retirer à la main est ce qui
supprime les clés.
