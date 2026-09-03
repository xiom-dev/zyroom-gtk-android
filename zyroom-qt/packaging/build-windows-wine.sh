#!/usr/bin/env bash
#
# Construit le paquet Windows depuis Linux, via Wine.
#
#   packaging/build-windows-wine.sh
#
# **Ce n'est pas la voie de reference.** Ce qui sort d'ici n'a jamais tourne
# sur un vrai Windows : Wine est une reimplementation, et ce qu'il laisse
# passer n'est pas toujours ce que Windows accepte. Le workflow
# .github/workflows/zyroom-qt-windows.yml construit sur une machine pretee par
# GitHub, et c'est celui-la qui fait foi. Celui-ci sert a avoir de quoi
# a essayer tout de suite, sans attendre ni pousser.
#
# **Wine ne fournit pas ICU, et Qt6 en depend.** Windows 10 et 11 embarquent
# icuuc.dll dans System32 ; PySide6 compte dessus et ne l'emporte pas dans sa
# roue. Sous Wine, l'import de QtCore echoue donc par un laconique "Module
# introuvable". Le script va chercher ICU4C et le pose dans le prefixe, sous
# ses deux noms : celui que Qt demande (icuuc.dll) et celui qu'ICU se donne a
# lui-meme (icuuc74.dll), car le premier reclame le second.
#
# Le paquet produit, lui, n'embarque aucune de ces DLL : sur un vrai Windows
# elles viennent du systeme. C'est verifiable -- `find dist -iname 'icu*.dll'`
# ne doit rien rendre.
set -euo pipefail

# Sans cela, un __init__.py reecrit dans la meme seconde garde son .pyc
# et la construction embarque le numero de version precedent.
export PYTHONDONTWRITEBYTECODE=1

racine=$(cd "$(dirname "$0")/.." && pwd)
cd "$racine"

base=${WINE_BASE:-$racine/../.wine-zyroom-qt}
mkdir -p "$base"
base=$(cd "$base" && pwd)
export WINEPREFIX="$base/prefixe"
export WINEDEBUG=-all
export WINEARCH=win64

py_version=3.12.8
icu_version=74
icu_url="https://github.com/unicode-org/icu/releases/download/release-74-2/icu4c-74_2-Win64-MSVC2019.zip"
python_url="https://www.python.org/ftp/python/$py_version/python-$py_version-amd64.exe"
python_exe="$WINEPREFIX/drive_c/users/$USER/AppData/Local/Programs/Python/Python312/python.exe"

command -v wine >/dev/null || { echo "Wine n'est pas installe." >&2; exit 1; }

if [ ! -f "$python_exe" ]; then
    echo "== Prefixe Wine =="
    wineboot -i >/dev/null 2>&1 || true
    sleep 3

    echo "== Python $py_version (Windows) =="
    installeur="$base/python-$py_version-amd64.exe"
    [ -f "$installeur" ] || curl -fsSL -o "$installeur" "$python_url"
    wine "$installeur" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 \
         Include_launcher=0 Shortcuts=0 AssociateFiles=0 >/dev/null 2>&1 || true
    sleep 5
    [ -f "$python_exe" ] || { echo "Python introuvable apres installation." >&2; exit 1; }

    echo "== PySide6 et PyInstaller =="
    wine "$python_exe" -m pip install --quiet --upgrade pip
    wine "$python_exe" -m pip install --quiet PySide6-Essentials pyinstaller
fi

systeme="$WINEPREFIX/drive_c/windows/system32"
if [ ! -f "$systeme/icuuc.dll" ]; then
    echo "== ICU (absent de Wine, indispensable a Qt6) =="
    [ -f "$base/icu4c.zip" ] || curl -fsSL -o "$base/icu4c.zip" "$icu_url"
    rm -rf "$base/icu4c" && unzip -qo "$base/icu4c.zip" -d "$base/icu4c"
    # Les deux noms : Qt demande icuuc.dll, qui reclame a son tour icudt74.dll.
    cp "$base/icu4c/bin64/"*.dll "$systeme/"
    for nom in icuuc icuin icudt; do
        cp "$base/icu4c/bin64/${nom}${icu_version}.dll" "$systeme/${nom}.dll"
    done
fi

wine "$python_exe" -c "from PySide6 import QtCore" 2>/dev/null || {
    echo "Qt ne se charge pas dans ce prefixe : voir le commentaire sur ICU." >&2
    exit 1
}

echo "== Icones =="
wine "$python_exe" packaging/icone.py
echo "== Traductions =="
wine "$python_exe" build_i18n.py >/dev/null
echo "== Verification du noyau =="
outils/sync-noyau.sh --verifie

# Le paquet Linux deja construit est mis de cote : le spec ecrit dans dist/,
# et l'ecraser ferait perdre l'archive qu'on vient de livrer.
#
# Un dist.linux qui traine vient d'une execution interrompue avant la
# restitution. Le laisser en place ferait echouer la mise de cote en silence,
# et le `rm -rf dist` d'apres emporterait le paquet Linux du jour -- c'est
# arrive. On le rapatrie donc avant de repartir.
if [ -d dist.linux ]; then
    echo "  (un paquet Linux mis de cote attendait son retour : repris)"
    mkdir -p dist
    cp -a dist.linux/. dist/
    rm -rf dist.linux
fi
if [ -d dist ]; then
    mv dist dist.linux
fi
rm -rf build dist

echo "== PyInstaller =="
# Wine herite du dossier courant : place ici, il voit Z:\home\... et le spec,
# qui calcule ses chemins depuis le dossier courant, tombe juste.
wine "$python_exe" -m PyInstaller --noconfirm --clean \
     packaging/zyroom-qt.spec 2>&1 | tail -3

if [ ! -f dist/ZyRoom-Qt/ZyRoom-Qt.exe ]; then
    echo "Echec : aucun executable produit." >&2
    rm -rf dist
    [ -d dist.linux ] && mv dist.linux dist
    exit 1
fi

version=$("$racine/.venv/bin/python" -c "import zyroom; print(zyroom.__version__)")

# Le dossier de la fois d'avant doit disparaitre avant le renommage : `mv` sur
# un dossier existant ne le remplace pas, il glisse la source *dedans*. On se
# retrouvait avec dist.windows/dist/ tandis que dist.windows/ZyRoom-Qt gardait
# la construction precedente -- et l'archive du chef emportait un executable
# vieux d'une version.
rm -rf dist.windows
mv dist dist.windows
if [ -d dist.linux ]; then
    mv dist.linux dist
fi
mkdir -p dist
# Le fichier qui cree les raccourcis, a cote de l'executable.
cp data/lanceurs/Installer.bat dist.windows/ZyRoom-Qt/

# L'executable doit etre plus recent que le spec qui vient de le produire :
# sinon c'est qu'on empaquette une construction ancienne, et le numero de
# version de l'archive mentirait.
if [ packaging/zyroom-qt.spec -nt dist.windows/ZyRoom-Qt/ZyRoom-Qt.exe ]; then
    echo "Echec : dist.windows/ZyRoom-Qt/ZyRoom-Qt.exe est plus vieux que le" >&2
    echo "spec -- la construction n'a pas abouti la ou on la cherche." >&2
    exit 1
fi

( cd dist.windows && zip -qry "../dist/ZyRoom-Qt-${version}-windows.zip" ZyRoom-Qt )

echo
echo "Dossier : dist.windows/ZyRoom-Qt/ZyRoom-Qt.exe"
echo "Archive : dist/ZyRoom-Qt-${version}-windows.zip"
echo
echo "Pour l'essayer : WINEPREFIX=$WINEPREFIX wine dist.windows/ZyRoom-Qt/ZyRoom-Qt.exe --diagnostic"
