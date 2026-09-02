#!/usr/bin/env bash
#
# Fabrique l'archive du chef de guilde, a partir d'un paquet deja construit.
#
#   packaging/paquet-chef.sh windows     depuis dist.windows/
#   packaging/paquet-chef.sh linux       depuis dist/
#
# **Une archive a part, et non un fichier de plus dans celle de la guilde.**
# Le lanceur leve le masque des coffres reserves : le poser dans le paquet que
# tout le monde telecharge, c'est donner a tout le monde ce qui ne regarde que
# le chef. Il faut deux archives, et une seule adresse annoncee sur la page.
set -euo pipefail
racine=$(cd "$(dirname "$0")/.." && pwd)
cd "$racine"

systeme=${1:-windows}
case $systeme in
    windows) source=dist.windows ; lanceur=ZyRoom-Qt-dev.bat ;;
    linux)   source=dist         ; lanceur=ZyRoom-Qt-dev.sh  ;;
    *) echo "Usage : $0 [windows|linux]" >&2 ; exit 2 ;;
esac

[ -d "$source/ZyRoom-Qt" ] || {
    echo "Erreur : $source/ZyRoom-Qt absent. Construisez d'abord." >&2
    exit 1
}

version=$("$racine/.venv/bin/python" -c "import zyroom; print(zyroom.__version__)")
travail=$(mktemp -d)
trap 'rm -rf "$travail"' EXIT

cp -a "$source/ZyRoom-Qt" "$travail/ZyRoom-Qt"
cp "data/lanceurs/$lanceur" "$travail/ZyRoom-Qt/"
[ "$systeme" = linux ] && chmod +x "$travail/ZyRoom-Qt/$lanceur"

nom="ZyRoom-Qt-${version}-${systeme}-chef.zip"
( cd "$travail" && zip -qry "$racine/dist/$nom" ZyRoom-Qt )
echo "Archive du chef : dist/$nom  ($(du -h "dist/$nom" | cut -f1))"
