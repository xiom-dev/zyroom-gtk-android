"""La barre d'attente, peinte à la main pour ressembler à celle de GTK.

**Pourquoi ne pas se contenter d'une `QProgressBar` indéterminée.** Elle
répète le motif de son `chunk` pour remplir la zone qu'elle lui alloue : avec
un curseur de neuf pixels, Qt en dessinait trois côte à côte, et l'on voyait
plusieurs curseurs balayer de front là où GTK n'en promène qu'un. Sans largeur
déclarée, il n'y en a bien qu'un, mais large de la moitié de la barre. Aucun
réglage de feuille de style ne donne un bloc unique de la bonne taille.

Trente lignes de peinture donnent ce que le style ne sait pas faire, et
suppriment du même coup les trois autres écarts : la couleur du fond, le
liseré du curseur et le rayon des coins.

Ce que fait GTK, et qu'on rejoue ici :

  - le fond vient d'Adwaita — #282828, coins de 4 pixels ;
  - le curseur occupe `PAS` de la largeur, soit 15 %, peint dans la sarcelle
    de l'application et cerné du bleu qu'Adwaita donne aux barres ;
  - il avance d'un `PAS` toutes les 100 millisecondes et **revient au départ**
    avant d'atteindre le bord, pour courir toujours dans le même sens.
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

from .theme import COULEURS

#: La fraction de la barre qu'occupe le curseur, et dont il avance à chaque
#: battement. C'est le `set_pulse_step` de la version GTK.
PAS = 0.15

#: Le battement, en millisecondes. Le `timeout_add` de la version GTK.
CADENCE = 100

#: Le fond et le liseré viennent du thème Adwaita, que la version GTK ne
#: remplace pas : elle ne change que la couleur de remplissage.
FOND = "#282828"
LISERE = "#15539e"
RAYON = 4.0


def positions() -> int:
    """Combien de positions le curseur occupe avant de revenir au départ.

    Sept positions à 0,15 : six pas pleins, puis un dernier raccourci pour que
    le curseur **touche le bord droit**. Le compte précédent — cinq positions —
    l'arrêtait aux trois quarts de la barre, et il repartait de là : on voyait
    un curseur qui n'allait jamais au bout.
    """
    import math

    return math.ceil((1.0 - PAS) / PAS) + 1


def decalage(position: int) -> float:
    """Où commence le curseur, en fraction de la barre.

    Le dernier pas est **borné** : sans cela le curseur dépasserait le bord et
    serait dessiné à cheval sur le vide.
    """
    return min(PAS * position, 1.0 - PAS)


class BarreAttente(QWidget):
    """Un curseur qui court de gauche à droite tant qu'on attend."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._position = 0
        self._minuteur = QTimer(self)
        self._minuteur.setInterval(CADENCE)
        self._minuteur.timeout.connect(self._battre)
        self.setVisible(False)

    def setVisible(self, visible: bool) -> None:      # noqa: N802 -- nom Qt
        """Le minuteur ne tourne que quand la barre se voit.

        Peindre pour personne coûterait un réveil toutes les dix fois par
        seconde, et la barre passe l'essentiel de son temps cachée.
        """
        super().setVisible(visible)
        if visible:
            self._position = 0
            self._minuteur.start()
        else:
            self._minuteur.stop()

    def _battre(self) -> None:
        self._position = (self._position + 1) % positions()
        self.update()

    def paintEvent(self, evenement) -> None:          # noqa: N802 -- nom Qt
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        cadre = QRectF(self.rect())

        peintre.setPen(Qt.PenStyle.NoPen)
        peintre.setBrush(QColor(FOND))
        peintre.drawRoundedRect(cadre, RAYON, RAYON)

        largeur = cadre.width() * PAS
        depart = cadre.width() * decalage(self._position)
        curseur = QRectF(depart, 0.0, largeur, cadre.height())
        # Le liseré est peint à l'intérieur : sans ce retrait d'un demi-pixel,
        # Qt le centre sur le bord et la moitié tombe hors du curseur.
        curseur = curseur.adjusted(0.5, 0.5, -0.5, -0.5)
        peintre.setPen(QColor(LISERE))
        peintre.setBrush(QColor(COULEURS["sarcelle"]))
        peintre.drawRoundedRect(curseur, RAYON, RAYON)
