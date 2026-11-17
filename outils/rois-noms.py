#!/usr/bin/env python3
"""Les noms des rois du catalogue PadUI, pour le depot du releve des rois
(xiom.be/padui/deposer.php) :
  rois-noms.js   lu par deposer.js (window.ROIS_NOMS), accents en \\u : le
                 fichier peut etre servi sans jeu de caracteres ;
  rois-noms.json lu par commun.php pour verifier les noms recus.

    python3 ~/jeu/ryzom/zyroom/xiom-dev/outils/rois-noms.py

A relancer quand le catalogue des rois change (paquet/donnees/catalogue.json
de l'installateur PadUI)."""
import json
import os

CATALOGUE = os.path.expanduser("~/jeu/ryzom/padui/installeur/paquet/donnees/catalogue.json")
SITE = os.path.expanduser("~/jeu/ryzom/xiom-dev/site-domaine/padui")

noms = sorted(n for n, roi in json.load(open(CATALOGUE, encoding="utf-8")).items() if roi)
with open(os.path.join(SITE, "rois-noms.json"), "w", encoding="utf-8") as f:
    json.dump(noms, f, ensure_ascii=False)
with open(os.path.join(SITE, "rois-noms.js"), "w", encoding="ascii") as f:
    f.write("// Ecrit par outils/rois-noms.py : les rois du catalogue PadUI.\n")
    f.write("window.ROIS_NOMS = " + json.dumps(noms, ensure_ascii=True) + ";\n")
print(f"{len(noms)} rois : rois-noms.js et rois-noms.json dans {SITE}")
