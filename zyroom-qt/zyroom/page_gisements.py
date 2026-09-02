"""Où sort une matière : nos propres marqueurs sur la carte d'Atys.

On embarquait autrefois les vues rendues par le tracker — trois mégaoctets
d'images figées. Ballistic Mystix a donné les coordonnées : sept kilooctets,
notre carte, et un zoom libre.

**Le nom du lieu est écrit aussi**, parce qu'un point ne dit pas où aller. Les
coordonnées, elles, ne le sont pas : le jeu ne permet pas de taper une position
pour y poser un repère, et deux nombres qu'on ne peut ni saisir ni recopier
nulle part n'apprennent rien.
"""
from __future__ import annotations

import html

from PySide6.QtWidgets import (QDialog, QGridLayout, QLabel, QVBoxLayout,
                               QWidget)

from . import carte, gisements
from .carte_widget import POINT, CarteAtys, cible, texte_cerne
from .i18n import _

#: La part du cadre qu'occupe le semis de points au premier affichage.
CADRAGE = 0.55

#: En deca de cette distance a l'ecran, deux gisements n'en font qu'un : deux
#: points d'une meme zone tombent sur le meme pixel a l'echelle 1, et deux
#: noms superposes ne se lisent plus.
SEUIL_GROUPE = 40.0


class CarteGisements(CarteAtys):
    """La carte, cadrée sur les gisements dès qu'elle connaît sa taille."""

    def __init__(self, points: list) -> None:
        super().__init__(self._peindre, hauteur=340)
        self._points = points
        self._cadre_fait = False

    def _pixels(self) -> list:
        sortie = []
        for x, y, _lieu in self._points:
            point = carte.pixel(x, y)
            if point is not None:
                sortie.append(point)
        return sortie

    def _peindre(self, peintre, echelle: float, marge_x: float,
                 marge_y: float) -> None:
        # Le cadrage au premier dessin : avant, le widget n'a pas de taille.
        if not self._cadre_fait:
            self._cadre_fait = True
            self.cadrer(self._pixels(), CADRAGE)
            return                    # le cadrage a redemande un dessin

        vus: dict[tuple[int, int], list] = {}
        for x, y, lieu in self._points:
            point = carte.pixel(x, y)
            if point is None:
                continue
            px = marge_x + point[0] * echelle
            py = marge_y + point[1] * echelle
            cle = (int(px / SEUIL_GROUPE), int(py / SEUIL_GROUPE))
            if cle in vus:
                vus[cle][3] += 1
            else:
                vus[cle] = [px, py, lieu, 1]

        for px, py, lieu, nombre in vus.values():
            if not (-40 <= px <= self.width() + 40
                    and -40 <= py <= self.height() + 40):
                continue
            cible(peintre, px, py, POINT)
            texte_cerne(peintre, px + 11, py - 7,
                        lieu if nombre == 1 else f"{lieu} ×{nombre}")


def montrer(parent, qualite: str, famille: str, matiere: str) -> None:
    """Ouvre la carte des gisements d'une matière."""
    points = gisements.points(qualite, famille, matiere)
    if not points:
        return

    fen = QDialog(parent)
    fen.setWindowTitle(f"{matiere} — {famille}")
    fen.resize(720, 640)
    colonne = QVBoxLayout(fen)
    colonne.setContentsMargins(10, 10, 10, 10)
    colonne.setSpacing(10)

    mot = _("Suprême") if qualite == "supreme" else _("Excellente")
    fourchettes = gisements.humidites(qualite, famille, matiere)
    # Sans espace autour du tiret, et la virgule decimale du francais : deux
    # fourchettes doivent tenir sur la ligne du titre.
    humidite = ", ".join(f"{bas:g}–{haut:g} %".replace(".", ",")
                         for bas, haut in fourchettes)
    entete = QLabel(
        f"<b>{html.escape(mot)}</b>"
        + (f"  ·  {_('humidité')} {html.escape(humidite)}" if humidite else "")
        + f"  ·  {len(points)} "
        + (_("gisements") if len(points) > 1 else _("gisement")))
    entete.setWordWrap(True)
    colonne.addWidget(entete)

    colonne.addWidget(CarteGisements(points), 1)

    # Les lieux, sur deux colonnes : les gisements vont jusqu'a cinq lieux, et
    # une colonne unique repousserait l'attribution hors de la fenetre.
    lieux = list(dict.fromkeys(lieu for _x, _y, lieu in points))
    porteur = QWidget()
    grille = QGridLayout(porteur)
    grille.setContentsMargins(0, 0, 0, 0)
    grille.setHorizontalSpacing(24)
    grille.setVerticalSpacing(2)
    grille.setColumnStretch(0, 1)
    grille.setColumnStretch(1, 1)
    rangs = max(1, (len(lieux) + 1) // 2)
    for rang, lieu in enumerate(lieux):
        lbl = QLabel(lieu)
        lbl.setObjectName("compact")
        grille.addWidget(lbl, rang % rangs, rang // rangs)
    colonne.addWidget(porteur)

    credit = QLabel(_("Positions : relevé de ballisticmystix.net, avec "
                      "l'accord de son auteur"))
    credit.setObjectName("discret")
    credit.setWordWrap(True)
    colonne.addWidget(credit)

    # Non modale : on compare volontiers deux matieres cote a cote.
    fen.setModal(False)
    fen.show()
