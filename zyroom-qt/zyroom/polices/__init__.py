"""La police du titre, embarquée avec l'application.

**Pourquoi l'embarquer.** Pirata One n'est installée sur presque aucun système,
ni sous Linux ni sous Windows : sans ce fichier, le nom de l'application
s'écrirait dans la police courante et le portage ne ressemblerait plus aux
autres.

**Ce qui change par rapport à la version GTK.** GTK n'a pas d'interface pour
charger un fichier de police : il fallait passer par fontconfig, sa
bibliothèque C, appelée à travers `ctypes` — et fontconfig n'existe pas sous
Windows. Qt, lui, tient son propre catalogue et sait lire un fichier
directement. Quarante lignes de bricolage deviennent un appel.

La SIL Open Font License veut que son texte voyage avec la police : il est à
côté, dans `OFL-PirataOne.txt`, et l'À propos nomme ses auteurs.
"""
from __future__ import annotations

import os

from PySide6.QtGui import QFontDatabase

#: Le nom sous lequel la police se declare, tel que Qt le rendra.
FAMILLE = "Pirata One"

FICHIER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "pirata_one.ttf")


def charger() -> bool:
    """Ajoute la police au catalogue de l'application. Rend vrai si c'est fait.

    Comme dans la version GTK, un échec n'est pas une erreur : l'application
    s'écrit alors dans la police du système, ce qui est laid mais pas cassé.
    """
    if not os.path.isfile(FICHIER):
        return False
    return QFontDatabase.addApplicationFont(FICHIER) != -1
