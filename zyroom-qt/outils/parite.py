#!/usr/bin/env python3
"""Confronte l'aspect de ZyRoom-Qt à celui de ZyRoom-GTK. GTK fait foi.

    ./outils/parite.py            compare, et dit ce qui diffère
    ./outils/parite.py --details  montre aussi tout ce qui concorde

Rend zéro quand les deux applications s'accordent, un sinon — c'est ce qui
permet à `livraison.sh` de s'arrêter plutôt que d'envoyer aux joueurs une
version qui a dérivé.

**Pourquoi ce contrôle existe.** Tous les écarts d'aspect trouvés jusqu'ici
l'ont été à l'œil, par Ludo, après livraison : une jauge étirée sur toute la
hauteur d'une rangée, une ligne de saison en gras qui la rendait floue, un
vert à un point du bon, un bouton qui ne s'allumait pas. Chacun se voyait
pourtant dans une mesure. Ce que l'œil trouve après coup, une mesure le trouve
avant.

**Aucune exception.** Il n'y a pas de liste d'écarts tolérés, et il ne doit pas
y en avoir : ce qui est relevé doit être identique, sans dérogation. C'est le
choix des propriétés relevées qui porte la décision, dans les deux fichiers de
`parite/`, et cette décision se discute là-bas — pas ici, au cas par cas, sous
la pression d'une livraison qui attend.

Les deux applications ne peuvent pas cohabiter dans un même processus : GTK
vit dans le Python du système, Qt dans son environnement virtuel. D'où deux
relevés lancés séparément, et cette confrontation de leurs résultats.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RELEVES = os.path.join(RACINE, "outils", "parite")

#: L'interpréteur de chaque application. Celui de Qt vit dans son
#: environnement virtuel ; celui de GTK est le Python du système, seul à
#: disposer de `gi`.
PYTHON_QT = os.path.join(RACINE, ".venv", "bin", "python")
PYTHON_GTK = "python3"


def relever(python: str, script: str, nom: str) -> dict | None:
    """Lance un relevé et rend son contenu, ou None s'il a échoué."""
    fait = subprocess.run([python, os.path.join(RELEVES, script)],
                          capture_output=True, text=True, timeout=300)
    if not fait.stdout.strip():
        print(f"Le relevé {nom} n'a rien rendu.", file=sys.stderr)
        if fait.stderr.strip():
            print(fait.stderr.strip()[-800:], file=sys.stderr)
        return None
    try:
        points = json.loads(fait.stdout)
    except json.JSONDecodeError as souci:
        print(f"Le relevé {nom} est illisible : {souci}", file=sys.stderr)
        return None
    if "erreur" in points:
        print(f"Le relevé {nom} a échoué : {points['erreur']}", file=sys.stderr)
        return None
    return points


def main() -> int:
    details = "--details" in sys.argv[1:]

    gtk = relever(PYTHON_GTK, "releve_gtk.py", "GTK")
    qt = relever(PYTHON_QT, "releve_qt.py", "Qt")
    if gtk is None or qt is None:
        return 1

    ecarts, accords = [], []
    for cle in sorted(set(gtk) | set(qt)):
        if cle not in gtk:
            ecarts.append((cle, "— (rien de tel en GTK)", qt[cle]))
        elif cle not in qt:
            ecarts.append((cle, gtk[cle], "— (absent de Qt)"))
        elif gtk[cle] != qt[cle]:
            ecarts.append((cle, gtk[cle], qt[cle]))
        else:
            accords.append((cle, gtk[cle]))

    if details:
        print(f"Ce qui concorde ({len(accords)} points) :")
        for cle, valeur in accords:
            print(f"  {cle:38} {valeur}")
        print()

    if not ecarts:
        print(f"Les deux applications s'accordent sur les {len(accords)} points "
              "relevés.")
        return 0

    print(f"{len(ecarts)} écart(s) sur {len(accords) + len(ecarts)} points "
          "relevés — GTK fait foi :\n", file=sys.stderr)
    for cle, cote_gtk, cote_qt in ecarts:
        print(f"  {cle}", file=sys.stderr)
        print(f"      GTK : {cote_gtk}", file=sys.stderr)
        print(f"      Qt  : {cote_qt}", file=sys.stderr)
    print("\nCorrigez Qt, ou retirez le point du relevé s'il n'a pas lieu "
          "d'être comparé.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
