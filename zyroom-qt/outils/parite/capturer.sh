#!/usr/bin/env bash
#
# Photographie les deux fenêtres, côte à côte, dans les mêmes conditions.
#
#   ./capturer.sh            les deux captures dans /tmp/parite-images
#   ./capturer.sh DOSSIER    ailleurs
#
# Le relevé point par point ne voit que ce qu'on pense à lui demander : onze
# écarts d'aspect ont été trouvés à l'œil par Ludo avant lui. Une image, elle,
# montre tout — encore faut-il pouvoir en obtenir une de la fenêtre GTK, qui
# ne se peint pas hors écran. D'où ce serveur X virtuel : les deux fenêtres y
# sont réellement affichées et rendues, sans que rien ne paraisse à l'écran.
#
# **Tout est normalisé, sinon la comparaison ne veut rien dire.** Un HOME de
# capture est monté de toutes pièces : même taille de fenêtre, même corps de
# police, mêmes entités, mêmes flux en cache. Sans cela on compare deux
# réglages — celui de Ludo met Qt à quinze points et GTK à onze, ce qui suffit
# à faire paraître tout Qt plus grand, sans qu'aucune ligne de code soit en
# cause.
set -euo pipefail

racine=$(cd "$(dirname "$0")/../../.." && pwd)
sortie=${1:-/tmp/parite-images}
[ "$sortie" = "--comme-le-bureau" ] && sortie=/tmp/parite-images
foyer=$sortie/home
ecran=:99
LARGEUR=1200
HAUTEUR=760
CORPS=11
# Le zoom a cent pour cent des deux cotes : c'est lui qui commande maintenant
# la taille du texte et celle des images ensemble, et deux fenetres zoomees
# differemment ne se comparent pas.

rm -rf "$sortie"
mkdir -p "$foyer/.config/zyroom-gtk" "$foyer/.config/zyroom-qt" \
         "$foyer/.cache/zyroom-gtk" "$foyer/.cache/zyroom-qt" \
         "$foyer/.local/share/zyroom-gtk" "$foyer/.local/share/zyroom-qt"

# Les mêmes réglages des deux côtés. `SyncOnStart=0` et `SyncInterval=0` : une
# capture ne doit pas dépendre du réseau ni de l'heure, et une resynchronisation
# en cours peindrait une barre d'attente sur l'une des deux images seulement.
for app in zyroom-gtk zyroom-qt; do
    cat > "$foyer/.config/$app/settings.ini" <<RÉGLAGES
[GENERAL]
WindowWidth = $LARGEUR
WindowHeight = $HAUTEUR
FontSize = $CORPS
Zoom = 100
SyncOnStart = 0
SyncInterval = 0
Notifications = 0
RÉGLAGES
done

# Les mêmes entités et les mêmes flux : deux fenêtres qui ne montrent pas le
# même personnage ne se comparent pas.
source_config=$HOME/.var/app/net.ryzom.zyroomgtk.dev/config/zyroom-gtk
source_cache=$HOME/.var/app/net.ryzom.zyroomgtk.dev/cache/zyroom-gtk
for app in zyroom-gtk zyroom-qt; do
    for fichier in characters.ini guilds.ini; do
        [ -f "$source_config/$fichier" ] && cp "$source_config/$fichier" \
            "$foyer/.config/$app/$fichier"
    done
    [ -d "$source_cache" ] && cp -r "$source_cache/." "$foyer/.cache/$app/" 2>/dev/null || true
done

demarrer_ecran() {
    Xvfb "$ecran" -screen 0 "${LARGEUR}x${HAUTEUR}x24" -dpi 96 >/dev/null 2>&1 &
    echo $!
    local essais=0
    until DISPLAY=$ecran xdpyinfo >/dev/null 2>&1 || [ $essais -gt 30 ]; do
        sleep 1
        essais=$((essais + 1))
    done
}

photographier() {   # $1 = nom, $2… = la commande
    local nom=$1
    shift
    local xpid
    xpid=$(demarrer_ecran | head -1)
    HOME=$foyer DISPLAY=$ecran $reglages "$@" >/dev/null 2>&1 &
    local app=$!
    # Le temps que la fenêtre se pose et que ses icônes arrivent du cache.
    sleep 14
    DISPLAY=$ecran import -window root "$sortie/$nom.png" 2>/dev/null || true
    kill "$app" 2>/dev/null || true
    kill "$xpid" 2>/dev/null || true
    sleep 1
}

# **Le banc mentait sur les tailles, et voici pourquoi.** Le HOME est bien
# jetable, mais `gsettings` ne le lit pas : il passe par dconf, donc par le bus
# de session, et rapportait les reglages reels du bureau. La version Qt les
# interroge -- l'agrandissement du texte, le theme d'icones -- et les
# appliquait donc ; la version GTK, elle, les attend d'un demon XSettings, que
# ce serveur X virtuel n'a pas. Sur un bureau regle a 1,25, les colonnes de Qt
# paraissaient trente pour cent plus larges que celles de GTK, alors que les
# deux fenetres sont identiques sur une vraie session.
#
# `GSETTINGS_BACKEND=memory` coupe court : les deux applications lisent alors
# les valeurs par defaut du schema, les memes pour l'une et pour l'autre.
#
#   ./capturer.sh --comme-le-bureau   garde au contraire les reglages reels
#
# Les deux les recoivent alors ensemble : c'est ce qu'il faut pour reproduire
# un defaut que le mainteneur voit chez lui, et que le banc neutre ne montre
# pas. Dans les deux cas, ce qui compte est que les deux fenetres soient
# logees a la meme enseigne.
reglages="env GSETTINGS_BACKEND=memory"
if [ "${1:-}" = "--comme-le-bureau" ] || [ "${2:-}" = "--comme-le-bureau" ]; then
    reglages="env"
    echo "Reglages du bureau conserves (agrandissement, theme d'icones)."
fi

echo "Capture de GTK…"
photographier gtk env GDK_BACKEND=x11 python3 "$racine/zyroom-gtk/run.py"

echo "Capture de Qt…"
photographier qt env QT_QPA_PLATFORM=xcb QT_FONT_DPI=96 \
    "$racine/zyroom-qt/.venv/bin/python" "$racine/zyroom-qt/run.py"

echo
for image in gtk qt; do
    if [ -f "$sortie/$image.png" ]; then
        echo "  $sortie/$image.png  $(identify -format '%wx%h' "$sortie/$image.png")"
    else
        echo "  $image : capture manquée" >&2
    fi
done
