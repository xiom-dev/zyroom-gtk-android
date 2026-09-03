#!/usr/bin/env bash
#
# Pose ZyRoom-Qt dans le menu des applications.
#
#   ./installer.sh              installe le raccourci
#   ./installer.sh --retirer    l'enleve
#
# Le paquet ne s'installe pas : il se decompresse ou l'on veut, et le
# raccourci pointe la ou il se trouve. Deplacer le dossier casse donc le
# raccourci -- relancez ce script depuis le nouvel emplacement.
set -euo pipefail

# Le dossier de ce script, meme appele par un chemin relatif ou depuis
# ailleurs : c'est lui qui contient l'executable.
ici=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
app=net.ryzom.zyroomqt
bureau=${XDG_DATA_HOME:-$HOME/.local/share}/applications/$app.desktop
icones=${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/256x256/apps

if [ "${1:-}" = "--retirer" ]; then
    rm -f "$bureau" "$icones/$app.png"
    update-desktop-database "$(dirname "$bureau")" 2>/dev/null || true
    echo "Raccourci retire. Le dossier de l'application, lui, reste ou il est."
    exit 0
fi

[ -x "$ici/ZyRoom-Qt" ] || {
    echo "Erreur : ZyRoom-Qt introuvable a cote de ce script." >&2
    echo "Gardez le dossier entier tel qu'il sort de l'archive." >&2
    exit 1
}

mkdir -p "$(dirname "$bureau")" "$icones"
[ -f "$ici/zyroom-qt.png" ] && cp "$ici/zyroom-qt.png" "$icones/$app.png"

# Exec sur un chemin absolu et entre guillemets : le dossier peut vivre dans
# "Mes documents" ou sous un nom accentue, et un chemin nu s'y couperait.
cat > "$bureau" <<DESKTOP
[Desktop Entry]
Type=Application
Name=ZyRoom-Qt
GenericName=Inventaires Ryzom
Comment=Consultez vos inventaires Ryzom et les coffres de la guilde, hors du jeu
Terminal=false
Categories=Game;
Keywords=Ryzom;inventaire;inventory;guilde;coffre;
StartupWMClass=$app
Exec="$ici/ZyRoom-Qt"
Path=$ici
Icon=$app
DESKTOP
chmod +x "$bureau"
update-desktop-database "$(dirname "$bureau")" 2>/dev/null || true

echo "ZyRoom-Qt est dans votre menu."
echo "Pour l'enlever : $0 --retirer"
