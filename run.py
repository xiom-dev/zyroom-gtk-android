#!/usr/bin/env python3
"""Point d'entrée de ZyRoom GTK.

Usage :
    ./run.py            lancement normal
    ./run.py --software  force le rendu logiciel (vieilles machines / pas de GPU)

Astuce : sur une machine sans accélération 3D fiable, GTK4 peut être forcé en
rendu logiciel via la variable d'environnement `GSK_RENDERER=cairo` (ce que fait
l'option --software ci-dessous).
"""
import os
import sys

if "--software" in sys.argv:
    sys.argv.remove("--software")
    os.environ.setdefault("GSK_RENDERER", "cairo")

from zyroom.app import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
