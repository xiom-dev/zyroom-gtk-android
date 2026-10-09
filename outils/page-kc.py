#!/usr/bin/env python3
"""Prepare KipeeCraft pour l'onglet de la page des MP, `site-domaine/mp/kc/`.

    python3 outils/page-kc.py

Deux sorties, a deposer sur xiom.be avec `kc.js` et `travail.js` :

- `kipeecraft.zip` : le coeur de kipeecraft-py (calcul, formats, donnees) et
  le pont `outils/kc_web.py`. Le Web Worker le deballe dans Pyodide. Ni
  l'interface GTK ni l'Evolver n'y servent ; l'Evolver est quand meme la,
  la Bijouterie emprunte ses filtres.
- `icones/` : les icones des types de matiere, reprises de KipeeCraft 1.2a.
- `kipee.png` : le logo, affiche en petit sous l'onglet.

**Pourquoi un zip et pas les fichiers un par un.** Pyodide sait deballer une
archive d'un seul appel ; une soixantaine de requetes pour autant de petits
fichiers prendrait plus de temps que le zip entier.
"""
from __future__ import annotations

import os
import shutil
import sys
import zipfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SORTIE = os.path.join(RACINE, "site-domaine", "mp", "kc")
PONT = os.path.join(RACINE, "outils", "kc_web.py")
PAQUET = os.path.expanduser("~/jeu/ryzom/KipeeCraft/kipeecraft-py/src/kipeecraft")

#: Ce qui part dans le zip, relativement au paquet.
GARDES = ("__init__.py", "paths.py", "core/", "formats/", "resources/patterns.json",
          "resources/defaults/")
#: Une date fixe : deux fabrications du meme code donnent le meme zip.
DATE = (2026, 1, 1, 0, 0, 0)


def fichiers():
    for dossier, sous, noms in os.walk(PAQUET):
        sous[:] = sorted(d for d in sous if d != "__pycache__")
        for nom in sorted(noms):
            chemin = os.path.join(dossier, nom)
            relatif = os.path.relpath(chemin, PAQUET).replace(os.sep, "/")
            if nom.endswith(".pyc"):
                continue
            if any(relatif == g or (g.endswith("/") and relatif.startswith(g))
                   for g in GARDES):
                yield chemin, "kipeecraft/" + relatif


def main() -> int:
    if not os.path.isdir(PAQUET):
        raise SystemExit(f"kipeecraft-py introuvable : {PAQUET}")
    os.makedirs(SORTIE, exist_ok=True)

    archive = os.path.join(SORTIE, "kipeecraft.zip")
    nombre = 0
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for chemin, nom in [*fichiers(), (PONT, "kc_web.py")]:
            info = zipfile.ZipInfo(nom, DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(chemin, "rb") as fh:
                z.writestr(info, fh.read())
            nombre += 1
    print(f"kipeecraft.zip : {nombre} fichiers, {os.path.getsize(archive) // 1024} ko")

    icones = os.path.join(SORTIE, "icones")
    os.makedirs(icones, exist_ok=True)
    source = os.path.join(PAQUET, "resources", "icons")
    for nom in sorted(os.listdir(source)):
        if nom.endswith(".png"):
            shutil.copy2(os.path.join(source, nom), os.path.join(icones, nom))
    print(f"icones/ : {len(os.listdir(icones))} images")
    # Le kipee de l'original, en logo sous l'onglet.
    shutil.copy2(os.path.join(PAQUET, "resources", "kipee.png"),
                 os.path.join(SORTIE, "kipee.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
