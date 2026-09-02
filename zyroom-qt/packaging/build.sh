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
rm -rf build dist
"$PYTHON" -m PyInstaller --noconfirm --clean packaging/zyroom-qt.spec

VERSION="$("$PYTHON" -c 'import zyroom; print(zyroom.__version__)')"
ARCH="$(uname -m)"
NOM="ZyRoom-Qt-${VERSION}-linux-${ARCH}"

echo "== Archive =="
# Un ZIP, et non un tar.gz : c'est le format que la mise a jour integree sait
# lire, sur les deux systemes. `zip -y` garde les liens symboliques tels
# quels, et les modes Unix -- dont le bit executable du binaire, sans lequel
# l'application mise a jour ne demarrerait pas.
( cd dist && zip -qry "${NOM}.zip" ZyRoom-Qt )
echo
echo "Dossier : dist/ZyRoom-Qt/ZyRoom-Qt"
echo "Archive : dist/${NOM}.zip  ($(du -h "dist/${NOM}.zip" | cut -f1))"
