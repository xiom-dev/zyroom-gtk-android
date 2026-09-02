#!/bin/sh
# ZyRoom-Qt, variante du chef de guilde.
#
# Elle montre les coffres que la version ordinaire masque -- le petit coffre
# de Nizy. C'est la seule difference : meme application, memes reglages, seul
# le masque tombe.
#
# Lancez ce fichier au lieu de ZyRoom-Qt.
ZYROOM_SHOW_ALL_CHESTS=1 exec "$(dirname "$0")/ZyRoom-Qt" "$@"
