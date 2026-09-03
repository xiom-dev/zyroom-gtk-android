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
# Les archives Windows vivent dans dist/ elles aussi, et PyInstaller veut un
# dist/ propre : sans cette mise a l'abri, construire pour Linux effacerait le
# paquet Windows du jour -- la reciproque du piege corrige dans
# build-windows-wine.sh, et pour la meme raison.
abri=$(mktemp -d)
for z in dist/*windows*.zip; do
    [ -f "$z" ] && mv "$z" "$abri/"
done
rm -rf build dist
"$PYTHON" -m PyInstaller --noconfirm --clean packaging/zyroom-qt.spec

VERSION="$("$PYTHON" -c 'import zyroom; print(zyroom.__version__)')"
ARCH="$(uname -m)"
NOM="ZyRoom-Qt-${VERSION}-linux-${ARCH}"

echo "== Installateur =="
# Le script qui pose le raccourci dans le menu, et l'icone dont il a
# besoin : tous deux a cote de l'executable, pas dans _internal, car
# c'est la que l'utilisateur les cherchera.
cp data/lanceurs/installer.sh dist/ZyRoom-Qt/
chmod +x dist/ZyRoom-Qt/installer.sh
cp packaging/zyroom-qt.png dist/ZyRoom-Qt/

echo "== Archive =="
# Un ZIP, et non un tar.gz : c'est le format que la mise a jour integree sait
# lire, sur les deux systemes. `zip -y` garde les liens symboliques tels
# quels, et les modes Unix -- dont le bit executable du binaire, sans lequel
# l'application mise a jour ne demarrerait pas.
( cd dist && zip -qry "${NOM}.zip" ZyRoom-Qt )
# Les archives Windows retrouvent leur place a cote de la nouvelle.
for z in "$abri"/*.zip; do
    [ -f "$z" ] && mv "$z" dist/
done
rmdir "$abri" 2>/dev/null || true
echo
echo "Dossier : dist/ZyRoom-Qt/ZyRoom-Qt"
echo "Archive : dist/${NOM}.zip  ($(du -h "dist/${NOM}.zip" | cut -f1))"
