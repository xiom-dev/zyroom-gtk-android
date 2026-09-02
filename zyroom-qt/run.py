#!/usr/bin/env python3
"""Point d'entrée de ZyRoom Qt.

Usage :
    ./run.py                lancement normal
    ./run.py --software     force le rendu logiciel (vieilles machines, VM)
    ./run.py --diagnostic   dit ce que l'application voit de son installation,
                            sans ouvrir de fenêtre — utile pour vérifier un
                            paquet construit sur une machine qu'on n'a pas
                            sous les yeux

Qt choisit tout seul sa plateforme d'affichage — Wayland ou X11 sous Linux,
Direct2D sous Windows. L'option ci-dessous ne sert qu'aux machines dont le
pilote 3D fait défaut : elle demande le rendu logiciel d'OpenGL, l'équivalent
du `GSK_RENDERER=cairo` de la version GTK.
"""
import os
import sys

if "--software" in sys.argv:
    sys.argv.remove("--software")
    os.environ.setdefault("QT_OPENGL", "software")
    os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")

if "--diagnostic" in sys.argv:
    from zyroom.diagnostic import main as diagnostic  # noqa: E402
    raise SystemExit(diagnostic())

from zyroom.app import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
