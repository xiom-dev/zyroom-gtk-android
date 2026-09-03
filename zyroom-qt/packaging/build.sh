#!/usr/bin/env bash
#
# Construit ZyRoom-Qt en dossier autonome, puis en archive.
#
# Depuis la racine du projet :
#     packaging/build.sh
#
# Le resultat : dist/ZyRoom-Qt/ (le dossier a distribuer) et l'archive
# dist/ZyRoom-Qt-<version>-linux-x86_64.tar.gz
#
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-.venv/bin/python}"
if [ ! -x "$PYTHON" ]; then
    echo "Environnement virtuel introuvable. Voir le README." >&2
    exit 1
fi

# Le noyau d'abord : construire une copie perimee du metier serait la
# meilleure facon de livrer un defaut deja corrige a cote.
echo "== Verification du noyau =="
outils/sync-noyau.sh --verifie

echo "== Icones =="
"$PYTHON" packaging/icone.py

echo "== Traductions =="
if [ -f build_i18n.py ]; then
    "$PYTHON" build_i18n.py
fi

echo "== PyInstaller =="
# Chaque systeme construit chez lui. PyInstaller ecrit dans le dossier que
# --distpath lui donne, et --workpath range de meme ses fichiers de travail :
# les deux constructions ne se croisent plus, et aucune n'a besoin d'effacer
# ce que l'autre vient de produire.
#
# dist/ ne recoit plus que les archives livrables. Personne ne l'efface en
# bloc, ce qui etait la source des trois accidents de septembre : un paquet
# Linux perdu, puis publie perime, et une archive du chef partie avec un
# executable vieux d'une version.
rm -rf build.linux dist.linux
"$PYTHON" -m PyInstaller --noconfirm --clean \
          --distpath dist.linux --workpath build.linux \
          packaging/zyroom-qt.spec

VERSION="$("$PYTHON" -c 'import zyroom; print(zyroom.__version__)')"
ARCH="$(uname -m)"
NOM="ZyRoom-Qt-${VERSION}-linux-${ARCH}"

echo "== Installateur =="
# Le script qui pose le raccourci dans le menu, et l'icone dont il a
# besoin : tous deux a cote de l'executable, pas dans _internal, car
# c'est la que l'utilisateur les cherchera.
cp data/lanceurs/installer.sh dist.linux/ZyRoom-Qt/
chmod +x dist.linux/ZyRoom-Qt/installer.sh
cp packaging/zyroom-qt.png dist.linux/ZyRoom-Qt/

echo "== Archive =="
# Un ZIP, et non un tar.gz : c'est le format que la mise a jour integree sait
# lire, sur les deux systemes. `zip -y` garde les liens symboliques tels
# quels, et les modes Unix -- dont le bit executable du binaire, sans lequel
# l'application mise a jour ne demarrerait pas.
mkdir -p dist
rm -f "dist/${NOM}.zip"
( cd dist.linux && zip -qry "../dist/${NOM}.zip" ZyRoom-Qt )
echo
echo "Dossier : dist.linux/ZyRoom-Qt/ZyRoom-Qt"
echo "Archive : dist/${NOM}.zip  ($(du -h "dist/${NOM}.zip" | cut -f1))"
