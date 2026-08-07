#!/usr/bin/env bash
# Installe (ou désinstalle) un lanceur de bureau pour l'utilisateur courant,
# pointant sur les sources — sans droits root ni paquet .deb.
#   ./install-user.sh              installe le lanceur
#   ./install-user.sh uninstall    le retire
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
APP_ID="net.ryzom.zyroomgtk"
APPS="$HOME/.local/share/applications"
ICONS="$HOME/.local/share/icons/hicolor/scalable/apps"
DESKTOP="$APPS/$APP_ID.desktop"
ICON="$ICONS/$APP_ID.svg"

refresh() {
    command -v update-desktop-database >/dev/null 2>&1 && \
        update-desktop-database "$APPS" 2>/dev/null || true
    command -v gtk-update-icon-cache >/dev/null 2>&1 && \
        gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
}

if [ "${1:-}" = "uninstall" ]; then
    rm -f "$DESKTOP" "$ICON"
    refresh
    echo "Lanceur retiré."
    exit 0
fi

mkdir -p "$APPS" "$ICONS"
python3 "$HERE/build_i18n.py" >/dev/null 2>&1 || true   # compile les traductions
install -m644 "$HERE/data/$APP_ID.svg" "$ICON"

cat > "$DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Name=ZyRoom GTK
GenericName=Ryzom inventory viewer
Comment=Consultez vos inventaires Ryzom hors-ligne
Comment[en]=View your Ryzom inventories offline
Exec=python3 $HERE/run.py
Icon=$APP_ID
Terminal=false
Categories=Game;
Keywords=Ryzom;inventaire;inventory;
StartupWMClass=$APP_ID
EOF
chmod +x "$DESKTOP"
refresh

echo "Lanceur installé : $DESKTOP"
echo "Il apparaît dans le menu des applications sous « ZyRoom GTK »."
