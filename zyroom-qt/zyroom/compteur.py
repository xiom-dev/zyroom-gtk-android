"""Le compteur des Options : un champ, puis un moins et un plus côte à côte.

**Pourquoi ne pas se contenter d'un `QSpinBox`.** Qt ne lui offre que deux
apparences : deux flèches empilées, ou — avec `ButtonSymbols.PlusMinus` — un
`+` et un `−` **également empilés**, minuscules, collés au bord droit du champ.
Le `Gtk.SpinButton` d'Adwaita, lui, pose deux boutons larges l'un **à côté** de
l'autre : `10 − +`. Aucun réglage ni aucune feuille de style ne fait passer les
boutons de Qt de la verticale à l'horizontale — ils sont dessinés par le style
natif, pas par la feuille.

Trente lignes donnent donc ce que le réglage ne sait pas faire : un champ, un
moins, un plus, dans cet ordre et sur une seule ligne. Les mesures viennent de
la fenêtre GTK, relevée au pixel : le fond `#1e2c31` d'un champ, des
séparateurs d'un pixel entre les trois parties, et des boutons de trente-cinq
pixels de large.

L'objet expose l'API d'un `QSpinBox` — `value`, `setValue`, `setRange`,
`setSingleStep`, `setSpecialValueText` — pour que la fenêtre d'Options ne voie
pas la différence.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractSpinBox, QHBoxLayout, QPushButton,
                               QSizePolicy, QSpinBox, QWidget)

#: La largeur des deux boutons, relevee sur la fenetre GTK.
LARGEUR_BOUTON = 35


class Compteur(QWidget):
    """Un compteur à la mode d'Adwaita : `[ 10 ][ − ][ + ]`."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("compteur")
        # Sans cet attribut, Qt ignore le fond et la bordure que la feuille
        # pose sur un widget nu : le compteur apparaissait sans son bloc, la
        # valeur flottant sur le fond de la fenetre. Ce n'est pas un detail de
        # style, c'est la regle -- QSS ne peint un QWidget que si on le lui
        # demande explicitement.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        ligne = QHBoxLayout(self)
        # Un pixel tout autour : la place de la bordure. Qt peint la bordure
        # d'une feuille de style *dans* le widget, sans l'ajouter a sa taille ;
        # sans ces marges le compteur faisait trente-deux pixels de haut la ou
        # le `Gtk.SpinButton` d'Adwaita en fait trente-quatre, et la rangee des
        # Options s'en trouvait deux pixels plus courte. Mesure.
        ligne.setContentsMargins(1, 1, 1, 1)
        ligne.setSpacing(0)

        self._champ = QSpinBox()
        self._champ.setObjectName("compteur-champ")
        # Sans boutons : ce sont les deux notres qui les remplacent.
        self._champ.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        # Quatre chiffres et l'air autour, soit les cinquante-deux pixels du
        # champ de GTK a dix points -- mesures. En caracteres et non en
        # pixels : grossie, la police emmene le champ avec elle.
        self._champ.setFixedWidth(
            self._champ.fontMetrics().horizontalAdvance("0") * 4 + 20)
        ligne.addWidget(self._champ)

        # Le vrai signe moins (U+2212) et non le trait d'union : c'est celui
        # qu'Adwaita dessine, et il a la largeur du plus.
        self._moins = QPushButton("−")
        self._plus = QPushButton("+")
        for bouton, sens in ((self._moins, -1), (self._plus, 1)):
            bouton.setObjectName("compteur-bouton")
            bouton.setFixedWidth(LARGEUR_BOUTON)
            # Le clic maintenu repete, comme dans GTK.
            bouton.setAutoRepeat(True)
            # Pas de tabulation sur les boutons : la touche passe du champ au
            # reglage suivant, comme dans la fenetre de reference.
            bouton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            bouton.clicked.connect(lambda _=False, s=sens: self._pas(s))
            ligne.addWidget(bouton)

        # Le compteur ne s'etire pas : le `Gtk.SpinButton` de la fenetre de
        # reference garde sa largeur naturelle, et la colonne qui s'etire est
        # celle des champs de texte. Etire, il rognait les libelles.
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._champ.valueChanged.connect(self._bornes)
        self._bornes()

    def _pas(self, sens: int) -> None:
        self._champ.setValue(
            self._champ.value() + sens * self._champ.singleStep())

    def _bornes(self, *_) -> None:
        """Le bouton s'éteint quand la borne est atteinte, comme dans GTK.

        Sur la fenêtre de référence, le `−` de « Resynchroniser » est gris tant
        que la valeur vaut zéro : le compteur dit ce qu'il peut encore faire.
        """
        self._moins.setEnabled(self._champ.value() > self._champ.minimum())
        self._plus.setEnabled(self._champ.value() < self._champ.maximum())

    # ------------------------------------------- l'API d'un QSpinBox
    def value(self) -> int:
        return self._champ.value()

    def setValue(self, valeur: int) -> None:          # noqa: N802 -- nom Qt
        self._champ.setValue(valeur)

    def setRange(self, mini: int, maxi: int) -> None:  # noqa: N802 -- nom Qt
        self._champ.setRange(mini, maxi)
        self._bornes()

    def setSingleStep(self, pas: int) -> None:         # noqa: N802 -- nom Qt
        self._champ.setSingleStep(pas)

    def setSpecialValueText(self, texte: str) -> None:  # noqa: N802 -- nom Qt
        self._champ.setSpecialValueText(texte)

    def minimum(self) -> int:
        return self._champ.minimum()

    def maximum(self) -> int:
        return self._champ.maximum()
