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

Chaque système construit chez lui : le dossier `ZyRoom-Qt/` prêt à copier
atterrit dans `dist.linux/` ou `dist.windows/` selon la cible, et `dist/` ne
reçoit que les archives `.zip` livrables.

Cette séparation n'est pas cosmétique. Les deux constructions ont longtemps
partagé `dist/`, que chacune nettoyait avant de travailler : construire pour
un système effaçait le paquet de l'autre. Un paquet Linux a ainsi été perdu
puis publié périmé, et une archive du chef est partie avec un exécutable
vieux d'une version.

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
unzip ZyRoom-Qt-*-linux-x86_64.zip -d ~/.local/lib/
~/.local/lib/ZyRoom-Qt/installer.sh          # entrée de menu et icône
~/.local/lib/ZyRoom-Qt/installer.sh --retirer  # pour l'enlever
```

Le script écrit le `.desktop` et l'icône sous le répertoire personnel, et rien
ailleurs. Il inscrit dans `Exec` le chemin d'où il a été lancé : déplacer le
dossier casse donc le raccourci, et il faut relancer le script depuis le
nouvel emplacement.

### Windows

Décompressez le `.zip` où vous voulez — `%LOCALAPPDATA%\Programs\ZyRoom-Qt`
est un choix raisonnable — puis lancez `ZyRoom-Qt.exe`. Rien n'est écrit dans
la base de registre.

`Installer.bat`, à côté de l'exécutable, pose un raccourci dans le menu
Démarrer et un autre sur le Bureau ; `Installer.bat /retirer` les enlève. Il
appelle PowerShell, seul moyen d'écrire un `.lnk` depuis un fichier de
commandes — et il vérifie ensuite que les raccourcis existent, plutôt que de
croire le code de retour, qui reste à zéro même quand PowerShell manque à
l'appel.

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
