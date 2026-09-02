"""Où sont les bêtes du joueur.

Un mektoub de bât laissé en pleine terre y reste, et son propriétaire finit par
oublier où. L'API donne sa position à chaque relevé ; c'est la seule chose
qu'elle sache dire d'un animal qu'on ne retrouve plus.

**Seule la carte dit où** : les coordonnées ne sont pas affichées. Le jeu ne
permet pas d'en saisir pour poser un repère, donc deux nombres de plus
n'auraient servi à rien.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QScrollArea, QVBoxLayout,
                               QWidget)

from . import carte
from .carte_widget import CarteAtys, POINT, POINT_JOUEUR, cible, texte_cerne
from .i18n import _

#: En deca de cette distance a l'ecran, deux betes n'en font qu'une.
#:
#: Quarante pixels : de quoi separer deux troupeaux laisses dans deux regions,
#: sans ecrire quatre fois le meme nom pour quatre mektoubs attaches ensemble.
SEUIL_GROUPE = 40.0


def etat_bete(bete) -> str:
    """L'état d'une bête, en français.

    La satiété n'a pas d'échelle documentée — les valeurs relevées vont de 54 à
    933 — donc on la donne telle quelle plutôt que d'inventer un pourcentage
    qui serait faux.
    """
    lieux = {"landscape": _("dehors"), "stable": _("à l'écurie"),
             "": _("état inconnu")}
    lieu = lieux.get(bete.statut, bete.statut)
    detail = f"{bete.etiquette} · {lieu}" if bete.nom else lieu
    if bete.satiete > 0:
        detail += _(" · satiété %d") % int(bete.satiete)
    return detail


class PageBetes(QWidget):
    def __init__(self, fenetre) -> None:
        super().__init__()
        self._fenetre = fenetre

        colonne = QVBoxLayout(self)
        colonne.setContentsMargins(0, 0, 0, 0)
        colonne.setSpacing(6)

        self._carte = CarteAtys(self._peindre_betes)
        colonne.addWidget(self._carte)

        self._entete = QLabel()
        self._entete.setObjectName("discret")
        self._entete.setContentsMargins(8, 0, 8, 0)
        colonne.addWidget(self._entete)

        # Deux colonnes : les mektoubs a gauche -- de monte comme de bat --,
        # les zigs a droite. On cherche rarement les uns en pensant aux
        # autres, et les zigs sont souvent nombreux.
        contenu = QWidget()
        duo = QHBoxLayout(contenu)
        duo.setContentsMargins(8, 0, 8, 8)
        duo.setSpacing(12)
        self._mektoubs = QVBoxLayout()
        self._zigs = QVBoxLayout()
        for pile in (self._mektoubs, self._zigs):
            porteur = QWidget()
            porteur.setLayout(pile)
            pile.setContentsMargins(0, 0, 0, 0)
            pile.setSpacing(0)
            duo.addWidget(porteur, 1)

        defilant = QScrollArea()
        defilant.setWidget(contenu)
        defilant.setWidgetResizable(True)
        defilant.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        colonne.addWidget(defilant, 1)

    # ---------------------------------------------------------- Contenu
    @staticmethod
    def _vider(pile: QVBoxLayout) -> None:
        while pile.count():
            element = pile.takeAt(0)
            if element.widget():
                element.widget().deleteLater()

    def rafraichir(self) -> None:
        for pile in (self._mektoubs, self._zigs):
            self._vider(pile)
        ent = self._fenetre.entite
        betes = list(getattr(ent, "betes", [])) if ent else []
        dehors = [b for b in betes if b.dehors]
        self._entete.setText(
            _("Aucune bête dehors : toutes sont rangées.") if not dehors
            else _("%d bête dehors") % len(dehors) if len(dehors) == 1
            else _("%d bêtes dehors") % len(dehors))
        self._remplir(self._mektoubs, _("Mektoubs"),
                      [b for b in betes if not b.zig])
        self._remplir(self._zigs, _("Zigs"), [b for b in betes if b.zig])
        self._carte.update()

    def _remplir(self, pile: QVBoxLayout, titre: str, betes: list) -> None:
        """Une colonne de bêtes, avec son titre. Vide, elle le dit."""
        entete = QLabel(f"{titre} · {len(betes)}")
        entete.setObjectName("peuple")
        entete.setContentsMargins(0, 0, 0, 4)
        pile.addWidget(entete)

        for rang, bete in enumerate(betes):
            rangee = QWidget()
            # Sans cet attribut, Qt ne peint pas le fond que la feuille
            # de style donne a un QWidget nu.
            rangee.setAttribute(
                Qt.WidgetAttribute.WA_StyledBackground, True)
            if rang % 2 == 0:
                rangee.setProperty("zebre", True)
            interieur = QVBoxLayout(rangee)
            interieur.setContentsMargins(8, 8, 8, 8)
            interieur.setSpacing(0)
            nom = QLabel(bete.nom or bete.etiquette)
            nom.setObjectName("titre")
            interieur.addWidget(nom)
            detail = QLabel(etat_bete(bete))
            detail.setObjectName("discret")
            detail.setWordWrap(True)
            interieur.addWidget(detail)
            pile.addWidget(rangee)

        if not betes:
            vide = QLabel(_("aucune"))
            vide.setObjectName("discret")
            vide.setContentsMargins(8, 8, 8, 8)
            pile.addWidget(vide)
        pile.addStretch(1)

    # ----------------------------------------------------------- Dessin
    def _peindre_betes(self, peintre, echelle: float, marge_x: float,
                       marge_y: float) -> None:
        """Les bêtes sur la carte, et le joueur en repère.

        Ce n'est pas une carte de navigation : elle sert à comprendre d'un coup
        d'œil dans quelle région une bête a été laissée.
        """
        ent = self._fenetre.entite
        if ent is None:
            return
        betes = [b for b in getattr(ent, "betes", [])
                 if b.dehors and carte.contient(b.x, b.y)]

        # Le joueur d'abord, sous les betes : c'est un repere, pas ce qu'on
        # cherche. Sa position est celle de sa derniere deconnexion.
        point = carte.pixel(ent.x, ent.y) if (ent.x or ent.y) else None
        if point is not None:
            jx = marge_x + point[0] * echelle
            jy = marge_y + point[1] * echelle
            if 0 <= jx <= self._carte.width() and 0 <= jy <= self._carte.height():
                cible(peintre, jx, jy, POINT_JOUEUR)
                texte_cerne(peintre, jx + 11, jy - 7, ent.name)

        # Les betes trop proches n'en font qu'une : quatre mektoubs attaches
        # ensemble tombent sur le meme pixel, et quatre noms superposes ne se
        # lisent plus.
        groupes: dict[tuple[int, int], list] = {}
        for bete in betes:
            point = carte.pixel(bete.x, bete.y)
            if point is None:
                continue
            cle = (int((marge_x + point[0] * echelle) / SEUIL_GROUPE),
                   int((marge_y + point[1] * echelle) / SEUIL_GROUPE))
            groupes.setdefault(cle, []).append(bete)

        for groupe in groupes.values():
            px, py = carte.pixel(groupe[0].x, groupe[0].y)
            x, y = marge_x + px * echelle, marge_y + py * echelle
            cible(peintre, x, y, POINT)
            nom = groupe[0].nom or groupe[0].etiquette
            if len(groupe) > 1:
                nom += f" +{len(groupe) - 1}"
            texte_cerne(peintre, x + 11, y - 7, nom)
