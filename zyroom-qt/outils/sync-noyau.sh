#!/usr/bin/env bash
#
# Recopie le noyau metier de zyroom-gtk vers zyroom-qt.
#
# La regle du portage : le noyau ne s'edite QUE dans zyroom-gtk. Ici on ne
# fait que le recopier. Toute modification faite du cote Qt sur un fichier
# de la liste NOYAU sera ecrasee sans avertissement au prochain appel.
#
# Usage :
#   outils/sync-noyau.sh            recopie
#   outils/sync-noyau.sh --verifie  ne recopie rien, dit ce qui differe
#
set -euo pipefail

ICI="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$(cd "$ICI/../zyroom-gtk" && pwd)"

if [ ! -d "$SOURCE/zyroom" ]; then
    echo "Introuvable : $SOURCE/zyroom" >&2
    exit 1
fi

# Les modules sans aucune dependance a la boite a outils graphique. Ils
# passent d'une interface a l'autre sans une ligne de changement.
NOYAU=(
    alerts.py armory.py backup.py carte.py categorydb.py enchantements.py
    gisements.py i18n.py meteo.py models.py movements.py namedb.py
    noms_avant_postes.py outposts.py partage.py pop.py roster.py
    ryzom_api.py sheetdb.py skills.py sorting.py volume.py watch.py
)

# Ce qui reste propre a Qt et que ce script ne doit JAMAIS toucher :
#   __init__.py     nomme le portage
#   config.py       chemins XDG cote GTK, %APPDATA% cote Windows
#   polices/        fontconfig via ctypes cote GTK, QFontDatabase cote Qt
#   icones.py       GLib.idle_add cote GTK, signal Qt en QueuedConnection ici
#   specialites.py  meme logique des deux cotes, mais sa moitie basse dessine
#                   les gouttes -- et le dessin ne se partage pas entre Cairo
#                   et QPainter
#   detail.py       la fiche d'un objet : memes sections, widgets Qt
#   options.py      memes reglages, widgets Qt
#   diagnostic.py    propre au portage : dit ce que voit un paquet construit
#   notifications.py  D-Bus par GLib cote GTK, icone de zone cote Qt
#   page_alertes.py  la cloche et les seuils, widgets Qt
#   chatlog.py       meme analyse et memes exports, fenetre Qt
#   updater.py       portail Flatpak cote GTK ; ici version.json et
#                    remplacement du dossier -- rien de commun
#   page_roster.py page_outposts.py page_skills.py page_betes.py
#   page_meteo.py page_gisements.py carte_widget.py   les ecrans de
#                   "Bonus", leurs cartes et le fond commun
#   theme.py fenetre.py app.py cles.py apropos.py   l'interface elle-meme

# Les traductions n'y sont plus : ce portage a son propre catalogue, bati par
# `build_i18n.py`, qui reprend celui de GTK et le complete de ses chaines a
# lui. Les recopier d'ici effacerait ce travail a chaque synchronisation.
RESSOURCES=(data cartes symboles)

VERIFIE=0
[ "${1:-}" = "--verifie" ] && VERIFIE=1

ecarts=0
for module in "${NOYAU[@]}"; do
    src="$SOURCE/zyroom/$module"
    dst="$ICI/zyroom/$module"
    if [ ! -f "$src" ]; then
        echo "MANQUE a la source : $module" >&2
        ecarts=$((ecarts + 1))
        continue
    fi
    if [ ! -f "$dst" ] || ! cmp -s "$src" "$dst"; then
        ecarts=$((ecarts + 1))
        if [ "$VERIFIE" = 1 ]; then
            echo "differe : $module"
        else
            cp -p "$src" "$dst"
            echo "copie   : $module"
        fi
    fi
done

for dossier in "${RESSOURCES[@]}"; do
    src="$SOURCE/zyroom/$dossier"
    [ -d "$src" ] || continue
    if [ "$VERIFIE" = 1 ]; then
        if ! diff -rq --exclude=__pycache__ "$src" "$ICI/zyroom/$dossier" \
             >/dev/null 2>&1; then
            echo "differe : $dossier/"
            ecarts=$((ecarts + 1))
        fi
    else
        # cp plutot que rsync : une dependance de moins, et rsync n'est
        # pas installe partout. Le dossier est refait a neuf pour qu'un
        # fichier retire a la source disparaisse aussi ici.
        rm -rf "$ICI/zyroom/$dossier"
        cp -a "$src" "$ICI/zyroom/$dossier"
        find "$ICI/zyroom/$dossier" -name __pycache__ -type d \
             -exec rm -rf {} + 2>/dev/null || true
    fi
done

# La police embarquee, sans le __init__.py qui la charge : le chargeur est
# propre a chaque boite a outils, le fichier .ttf est le meme.
if [ "$VERIFIE" != 1 ]; then
    cp -p "$SOURCE/zyroom/polices/pirata_one.ttf" \
          "$SOURCE/zyroom/polices/OFL-PirataOne.txt" "$ICI/zyroom/polices/"
fi

if [ "$VERIFIE" = 1 ]; then
    [ "$ecarts" = 0 ] && echo "Noyau a jour." || echo "$ecarts ecart(s)."
    exit 0
fi
echo "Noyau synchronise depuis $SOURCE"
