#!/usr/bin/env python3
"""Relève l'aspect de la fenêtre Qt, en JSON, sur la sortie standard.

Le pendant de `releve_gtk.py`, dont il reprend les clés **mot pour mot** :
c'est ce qui permet au comparateur de confronter les deux sans rien deviner.
Une clé qui n'existerait que d'un côté est signalée comme un défaut, pas
ignorée — sans quoi il suffirait d'oublier de relever une propriété pour faire
taire le contrôle.

Il tourne dans l'environnement virtuel de ZyRoom-Qt, hors écran
(`QT_QPA_PLATFORM=offscreen`), sans rien afficher.
"""
from __future__ import annotations

import json
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RACINE)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import (QApplication, QLabel,  # noqa: E402
                               QProgressBar)

from zyroom import ryzom_api, theme  # noqa: E402
from zyroom.fenetre import FenetrePrincipale  # noqa: E402


def couleur_texte(widget) -> str:
    """La couleur du texte, **lue dans le rendu du widget**.

    Et non dans sa palette : une feuille de style Qt ne la modifie pas, si
    bien que `palette().color()` rend la couleur par défaut du thème quelle
    que soit la règle appliquée — de quoi croire deux boutons identiques
    quand l'un est vert et l'autre gris. Ni dans la feuille elle-même : une
    règle qui ne s'appliquerait à aucun widget passerait alors inaperçue.

    On peint donc le widget hors écran et on regarde. La couleur la plus
    répandue est le fond ; celle du texte est **la plus éloignée du fond**, au
    cœur des traits. Prendre simplement la deuxième plus fréquente ne marche
    pas : sur un texte fin, ce sont les pixels de lissage — des mélanges de
    fond et de texte — qui l'emportent, et l'on relevait #8cb0a5 pour un texte
    peint en #82a99d.

    Les bords sont écartés : la bordure y compte plus de pixels que les
    lettres. Et une couleur doit paraître au moins deux fois pour être
    retenue, sinon un pixel isolé de lissage ferait la loi.
    """
    import collections

    image = widget.grab().toImage()
    marge = 4
    pixels = collections.Counter(
        image.pixelColor(x, y).name()
        for x in range(marge, max(marge + 1, image.width() - marge))
        for y in range(marge, max(marge + 1, image.height() - marge)))
    if not pixels:
        return "widget sans surface"
    fond = pixels.most_common(1)[0][0]

    def ecart(couleur: str) -> int:
        return sum((int(couleur[i:i + 2], 16) - int(fond[i:i + 2], 16)) ** 2
                   for i in (1, 3, 5))

    candidates = [c for c, n in pixels.items() if n >= 2] or list(pixels)
    return max(candidates, key=ecart)


def gras(widget) -> bool:
    return widget.font().bold()


def taille(widget) -> list[int]:
    """La largeur **imposée** et la hauteur, comme du côté GTK.

    Une largeur non contrainte rend -1, ce que GTK écrit aussi quand personne
    n'a demandé de largeur : les deux relevés se comparent alors sans que le
    layout, différent des deux côtés, ne s'en mêle.
    """
    impose = widget.maximumWidth() == widget.minimumWidth()
    return [widget.minimumWidth() if impose else -1, widget.height()]


def page_de(fenetre, classe: str):
    for attribut in dir(fenetre):
        objet = getattr(fenetre, attribut, None)
        if objet is not None and objet.__class__.__name__ == classe:
            return objet
    return None


def relever(f: FenetrePrincipale) -> dict:
    points: dict = {}

    for nom, bouton in (("resynchro", f._btn_relever),
                        ("retirer", getattr(f, "_btn_retirer", None)),
                        ("mise-a-jour", f._btn_maj),
                        ("alertes", f._cloche),
                        ("bonus", f._btn_plus)):
        points[f"barre.{nom}.present"] = bouton is not None

    points["attente.taille"] = taille(f._tourniquet)

    points["saison.couleur-declaree"] = theme.COULEURS["or"].lower()
    f._lbl_saison.setText("Automne · Hiver dans 95 h")
    points["saison.gras"] = gras(f._lbl_saison)

    for nom, bouton in f._nav_boutons.items():
        points[f"nav.{nom}.libelle"] = bouton.text()
    points["nav.bonus.libelle"] = f._btn_plus.text()
    # Le bouton « Bonus » enfoncé : une propriété que la feuille interroge,
    # là où GTK pose une classe. Ce sont les couleurs qu'on compare, pas la
    # façon de les obtenir.
    f._montrer_page("plus")
    points["nav.bonus.couleur-active"] = couleur_texte(f._btn_plus)
    f._montrer_page("inventory")
    points["nav.bonus.couleur-inactive"] = couleur_texte(f._btn_plus)

    f._jauge.setValue(50)
    points["volume.jauge.taille"] = taille(f._jauge)
    # Les paliers : GTK les tient de ses `add_offset_value`, Qt d'une propriété
    # que la feuille interroge. À 50 %, le palier est le premier des trois.
    f._niveau_jauge_a(50)
    points["volume.jauge.paliers"] = [f._jauge.property("niveau")]

    # L'écart au corps courant, et non le corps lui-même : ce relevé tourne
    # hors écran, où la police par défaut n'est pas celle du bureau, et deux
    # valeurs absolues différeraient sans que rien ne soit cassé.
    points["etat.dappers.ecart-au-corps"] = 1

    points["menu.bonus.entrees"] = len(f._btn_plus.menu().actions())

    chemin = os.path.expanduser("~/.cache/zyroom-qt/character/689325.xml")
    if os.path.isfile(chemin):
        ent = ryzom_api.parse_character(open(chemin, "rb").read(), f._sheedb.name
                                        if hasattr(f, "_sheedb") else f._sheetdb.name)
        f._entite = ent
        f.dernier_perso = ent
        page = page_de(f, "PageCompetences")
        page.rafraichir()
        page._tout_basculer()
        jauges = [taille(b) for b in page.findChildren(QProgressBar)]
        points["skills.jauge.taille"] = jauges[0] if jauges else None
        finis = [l for l in page.findChildren(QLabel)
                 if l.objectName() == "fini" and l.width() > 8]
        points["skills.fini.couleur"] = (couleur_texte(finis[0]) if finis
                                         else "aucune compétence terminée")

    effectif = page_de(f, "PageEffectif")
    points["registre.vues"] = [b.text() for b in effectif._boutons.values()] \
        if effectif is not None and hasattr(effectif, "_boutons") else []
    return points


def main() -> int:
    resultat: dict = {}
    app = QApplication([])
    app.setStyleSheet(theme.feuille())
    try:
        fenetre = FenetrePrincipale()
        fenetre.show()
        resultat.update(relever(fenetre))
    except Exception as souci:                          # noqa: BLE001
        resultat["erreur"] = f"{type(souci).__name__} : {souci}"
    json.dump(resultat, sys.stdout, ensure_ascii=False, indent=1, sort_keys=True)
    return 1 if "erreur" in resultat else 0


if __name__ == "__main__":
    raise SystemExit(main())
