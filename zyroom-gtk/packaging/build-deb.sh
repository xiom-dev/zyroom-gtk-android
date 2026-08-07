#!/usr/bin/env bash
# Construit un paquet .deb (Debian/Ubuntu) de ZyRoom GTK.
# Dépendances de build : make, dpkg-deb, fakeroot, python3.
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION="${VERSION:-6.0.0}"
MAINTAINER="${MAINTAINER:-ZyRoom GTK <ludopika@gmail.com>}"

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

make install DESTDIR="$STAGE" PREFIX=/usr

mkdir -p "$STAGE/DEBIAN"
INSTALLED_SIZE="$(du -sk "$STAGE/usr" | cut -f1)"
cat > "$STAGE/DEBIAN/control" <<EOF
Package: zyroom-gtk
Version: $VERSION
Section: games
Priority: optional
Architecture: all
Depends: python3 (>= 3.9), python3-gi, gir1.2-gtk-4.0
Installed-Size: $INSTALLED_SIZE
Maintainer: $MAINTAINER
Description: ZyRoom GTK - Ryzom inventory viewer
 View your Ryzom characters' and guilds' inventories offline via the
 Ryzom web API, with alerts, item details, chat-log analysis and backups.
 GTK4/Python port (AGPLv3) of Misugi's original zyRoom.
EOF

# Le nom du paquet lui-même reste « zyroom-gtk » : la charte Debian impose des
# minuscules. Seul le fichier livré porte le nom affiché de l'application.
OUT="ZyRoom-GTK_${VERSION}_all.deb"
fakeroot dpkg-deb --build "$STAGE" "$OUT"
echo "Paquet créé : $OUT"
