"""La jauge, peinte à la main, aux mesures exactes du `Gtk.LevelBar`.

**Pourquoi ne pas s'en tenir à une `QProgressBar` habillée par la feuille de
style.** Qt refuse de dessiner un `border-radius` quand le bloc rempli est
plus étroit que deux fois son rayon : sous une douzaine de pour cent, la
jauge des compétences perdait ses coins et redevenait un rectangle franc.
GSK, lui, réduit les rayons à la manière de CSS et arrondit un bloc de deux
pixels comme un autre — mesuré côté GTK, le coin d'une jauge à 3 % y est
antialiasé, le nôtre était plein.

Le reste est repris tel quel de la référence, y compris ce qui surprend :

- le bloc rempli n'est arrondi **qu'à gauche**, son bord droit reste franc.
  Adwaita l'écrit `border-radius: 5px 0 0 5px` en écriture gauche-droite, et
  cela vaut même à cent pour cent — le bloc déborde alors du coin arrondi du
  fond, et GTK ne l'en empêche pas ;
- le liseré d'un pixel se dessine à l'intérieur du bloc, comme un `border`
  CSS. C'est lui qui fait paraître bleue une compétence à peine entamée :
  à 3 %, ses deux pixels de large sont entièrement liseré, et le sarcelle
  n'a plus où se mettre. La version GTK peint exactement les mêmes pixels ;
- la largeur du bloc est tronquée, jamais arrondie : 10,8 pixels en font 10.
"""
from __future__ import annotations

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from . import theme

#: Le fond du creux, et les trois liseres des paliers. Ces quatre couleurs
#: viennent du Default-dark.css de GTK et non de notre palette : les reprendre
#: autrement aurait fait deux jauges cousines au lieu de deux jumelles.
FOND = "#282828"
LISERE_BAS = "#15539e"
LISERE_HAUT = "#15539e"
LISERE_PLEIN = "#26ab62"

#: Cinq pixels, le rayon qu'Adwaita donne au creux comme au bloc.
RAYON = 5.0


class Jauge(QWidget):
    """Un creux, un bloc rempli, un liseré. Rien de plus.

    L'interface reprend le peu qu'on utilisait de `QProgressBar` — `setValue`
    et une hauteur fixe — pour que les deux appels d'origine n'aient qu'à
    changer de classe.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._valeur = 0
        self._lisere = LISERE_HAUT
        # Onze pixels : neuf de bloc et un de lisere de part et d'autre.
        # **En pixels et non en hauteurs de ligne** : GTK pose ce nombre en
        # dur, et une jauge qui suivrait la police cesserait de lui ressembler
        # des qu'on change de corps.
        self.setFixedHeight(11)

    def value(self) -> int:
        return self._valeur

    def setValue(self, valeur: int) -> None:   # noqa: N802 -- nom de Qt
        valeur = max(0, min(100, int(valeur)))
        if valeur != self._valeur:
            self._valeur = valeur
            self.update()

    def lisere(self) -> str:
        return self._lisere

    def poser_lisere(self, couleur: str) -> None:
        """Le liseré du palier. Seule la jauge de volume en change."""
        if couleur != self._lisere:
            self._lisere = couleur
            self.update()

    # ------------------------------------------------------------- peinture
    @staticmethod
    def _bloc(x: float, y: float, largeur: float, hauteur: float,
              rayon: float) -> QPainterPath:
        """Le contour du bloc rempli : arrondi à gauche, franc à droite."""
        rayon = max(0.0, min(rayon, largeur, hauteur / 2))
        chemin = QPainterPath()
        if rayon <= 0.0:
            chemin.addRect(QRectF(x, y, largeur, hauteur))
            return chemin
        cote = 2 * rayon
        chemin.moveTo(x + largeur, y)
        chemin.lineTo(x + rayon, y)
        chemin.arcTo(QRectF(x, y, cote, cote), 90, 90)
        chemin.lineTo(x, y + hauteur - rayon)
        chemin.arcTo(QRectF(x, y + hauteur - cote, cote, cote), 180, 90)
        chemin.lineTo(x + largeur, y + hauteur)
        chemin.closeSubpath()
        return chemin

    def paintEvent(self, event) -> None:       # noqa: N802 -- nom impose
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        largeur = float(self.width())
        hauteur = float(self.height())

        creux = QPainterPath()
        rayon_creux = min(RAYON, hauteur / 2)
        creux.addRoundedRect(QRectF(0, 0, largeur, hauteur),
                             rayon_creux, rayon_creux)
        peintre.fillPath(creux, QColor(FOND))

        rempli = int(largeur * self._valeur / 100)
        if rempli <= 0:
            return

        # Les rayons se reduisent quand le bloc est trop etroit pour eux,
        # comme le fait CSS : a deux pixels de large, le rayon tombe a deux.
        rayon = min(RAYON, float(rempli))

        # Deux passes, et non un `drawPath` qui remplirait et tracerait d'un
        # coup : GTK peint d'abord le bloc jusqu'a son bord exterieur, puis
        # pose la bordure par-dessus. En une seule passe, le remplissage
        # s'arrete au milieu du trait et les coins arrondis ressortaient plus
        # pales que ceux de la reference.
        peintre.fillPath(self._bloc(0.0, 0.0, float(rempli), hauteur, rayon),
                         QColor(theme.COULEURS["sarcelle"]))
        # Un demi-pixel de retrait, pour que le trait d'un pixel tombe
        # exactement sur le pixel du bord au lieu de l'enjamber.
        peintre.strokePath(
            self._bloc(0.5, 0.5, rempli - 1.0, hauteur - 1.0, rayon - 0.5),
            QPen(QColor(self._lisere), 1))
