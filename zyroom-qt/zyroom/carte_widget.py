"""La carte d'Atys : une image qu'on agrandit, qu'on déplace, et qu'on annote.

Ce widget porte le fond de carte et les gestes ; ce qu'on pose dessus — des
bêtes, des gisements — est laissé à l'appelant, qui fournit une fonction de
dessin. C'est le `_peindre_carte` de la version GTK, partagé de la même façon
entre l'écran des bêtes et celui des gisements : même image, même mise à
l'échelle, même découpage.

**Trois façons d'agrandir, parce que trois matériels** : la molette de la
souris, le pincement du pavé tactile, et le glissement au bouton pour se
déplacer une fois agrandi. Le monde entier tient dans la hauteur d'une carte
de visite : sans agrandissement, deux bêtes séparées de cinq cents mètres sont
au même endroit.

**Ce que Qt fait autrement que GTK.** GTK attache des contrôleurs de gestes à
sa `DrawingArea` ; en Qt, on redéfinit les méthodes d'événement du widget. Le
pincement du pavé tactile arrive par `QNativeGestureEvent` là où le système en
émet, et par la molette ailleurs — les deux chemins mènent au même zoom.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QWidget

from . import carte

#: Jusqu'ou l'agrandissement va. Au-dela, on n'ajoute plus que du flou.
ZOOM_MAX = 6.0

#: Ce que gagne ou perd un cran de molette.
PAS_ZOOM = 1.1

#: Le noir des cernes et des liseres, jamais tout a fait noir pour l'oeil.
CERNE = QColor(15, 20, 23)

#: Le rouge du point. Il n'existe nulle part ailleurs sur la carte a ce ton.
POINT = QColor(255, 46, 46)

#: Le bleu du repere du joueur, distinct du rouge des betes.
POINT_JOUEUR = QColor(59, 156, 255)

BLANC = QColor(255, 255, 255)


def texte_cerne(peintre: QPainter, x: float, y: float, texte: str) -> None:
    """Un nom en blanc, cerné de noir sur ses huit côtés.

    C'est la solution des cartes de toujours, et la seule qui tienne ici : la
    carte passe du vert sombre des forêts au sable clair, au rouge du désert et
    au violet des zones corrompues, et l'or du thème s'y perdait. Deux
    décalages en diagonale laissaient le liseré manquant au-dessus et sur les
    côtés — il en faut huit.
    """
    if not texte:
        return
    police = QFont()
    police.setPointSize(10)
    peintre.setFont(police)
    peintre.setPen(CERNE)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx or dy:
                peintre.drawText(QPointF(x + dx * 1.2, y + dy * 1.2), texte)
    peintre.setPen(BLANC)
    peintre.drawText(QPointF(x, y), texte)


def cible(peintre: QPainter, x: float, y: float, coeur: QColor) -> None:
    """Un point à trois anneaux : cerne noir, disque blanc, cœur coloré.

    Aucune teinte unique ne se détache partout sur cette carte ; le contraste
    noir sur blanc, lui, tient sur tout.
    """
    peintre.setPen(Qt.PenStyle.NoPen)
    for rayon, couleur in ((7.0, CERNE), (5.5, BLANC), (3.0, coeur)):
        peintre.setBrush(couleur)
        peintre.drawEllipse(QPointF(x, y), rayon, rayon)


class CarteAtys(QWidget):
    """Le fond de carte, agrandissable et déplaçable.

    `dessus` est appelée après le fond, avec `(peintre, echelle, marge_x,
    marge_y)` : de quoi placer un point de la carte à l'écran.
    """

    #: L'image, chargee une fois pour toutes les cartes de l'application.
    _image: QPixmap | None = None

    def __init__(self, dessus=None, hauteur: int = 300) -> None:
        super().__init__()
        self._dessus = dessus
        self.setMinimumHeight(hauteur)
        self._zoom = 1.0
        self._glissement = [0.0, 0.0]
        self._depart_glisse = None
        self._depart_pince = None
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    # ------------------------------------------------------------- Image
    @classmethod
    def image(cls) -> QPixmap | None:
        if cls._image is None:
            image = QPixmap(carte.CHEMIN)
            cls._image = image if not image.isNull() else None
        return cls._image

    # -------------------------------------------------------------- Pose
    def pose(self) -> tuple | None:
        """`(échelle, marge_x, marge_y)`, ou None si l'image manque."""
        image = self.image()
        if image is None:
            return None
        largeur, hauteur = self.width(), self.height()
        if largeur <= 0 or hauteur <= 0:
            return None
        echelle = min(largeur / image.width(),
                      hauteur / image.height()) * self._zoom
        marge_x = (largeur - image.width() * echelle) / 2 + self._glissement[0]
        marge_y = (hauteur - image.height() * echelle) / 2 + self._glissement[1]
        return echelle, marge_x, marge_y

    def _borner(self) -> None:
        """Empêche la carte de s'échapper de son cadre.

        Le débord se mesure sur l'image telle qu'elle est dessinée, et non sur
        la largeur du cadre : la carte y tient en boîte aux lettres, et un
        débord calculé sur le cadre laissait la pousser dans le vide.
        """
        image = self.image()
        if image is None or self.width() <= 0 or self.height() <= 0:
            return
        echelle = min(self.width() / image.width(),
                      self.height() / image.height()) * self._zoom
        debord_x = max(0.0, (image.width() * echelle - self.width()) / 2)
        debord_y = max(0.0, (image.height() * echelle - self.height()) / 2)
        self._glissement[0] = max(-debord_x, min(debord_x, self._glissement[0]))
        self._glissement[1] = max(-debord_y, min(debord_y, self._glissement[1]))

    def cadrer(self, points: list, part: float = 0.55) -> None:
        """Cadre la vue sur un semis de points, une fois, au premier dessin.

        `points` est une liste de `(x, y)` en pixels de la carte. On ne peut
        pas cadrer à la construction : il faut connaître la taille du cadre, et
        elle n'existe qu'à la mesure.
        """
        image = self.image()
        if image is None or not points or self.width() <= 0:
            return
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        # Un seul gisement n'a pas d'etendue : on lui en donne une, sinon le
        # zoom partirait au maximum sur un point.
        large = max(max(xs) - min(xs), 300.0)
        haute = max(max(ys) - min(ys), 260.0)
        base = min(self.width() / image.width(), self.height() / image.height())
        if base <= 0:
            return
        voulue = min(part * self.width() / large, part * self.height() / haute)
        self._zoom = min(ZOOM_MAX, max(1.0, voulue / base))
        echelle = base * self._zoom
        self._glissement = [echelle * (image.width() / 2 - cx),
                            echelle * (image.height() / 2 - cy)]
        self._borner()
        self.update()

    def _regler_zoom(self, facteur: float) -> None:
        avant = self._zoom
        self._zoom = max(1.0, min(ZOOM_MAX, self._zoom * facteur))
        if self._zoom == avant:
            return
        # Le deplacement suit l'agrandissement, sinon la vue part sur le cote :
        # l'image grandit autour de son propre milieu, pas autour du notre.
        rapport = self._zoom / avant
        self._glissement[0] *= rapport
        self._glissement[1] *= rapport
        self._borner()
        self.update()

    # ---------------------------------------------------------- Dessin
    def paintEvent(self, _event) -> None:            # noqa: N802 -- nom Qt
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        peintre.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        # Le decoupage au cadre : agrandie, la carte deborde de toutes parts.
        peintre.setClipRect(QRectF(0, 0, self.width(), self.height()))

        pose = self.pose()
        if pose is None:
            return
        echelle, marge_x, marge_y = pose
        image = self.image()
        peintre.drawPixmap(
            QRectF(marge_x, marge_y,
                   image.width() * echelle, image.height() * echelle),
            image, QRectF(image.rect()))
        if self._dessus is not None:
            self._dessus(peintre, echelle, marge_x, marge_y)

    # ---------------------------------------------------------- Gestes
    def wheelEvent(self, event) -> None:             # noqa: N802 -- nom Qt
        cran = event.angleDelta().y()
        if cran:
            self._regler_zoom(PAS_ZOOM if cran > 0 else 1 / PAS_ZOOM)
        event.accept()

    def mousePressEvent(self, event) -> None:        # noqa: N802 -- nom Qt
        if event.button() == Qt.MouseButton.LeftButton:
            self._depart_glisse = (event.position(), list(self._glissement))
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event) -> None:         # noqa: N802 -- nom Qt
        if self._depart_glisse is None:
            return
        origine, depart = self._depart_glisse
        self._glissement[0] = depart[0] + (event.position().x() - origine.x())
        self._glissement[1] = depart[1] + (event.position().y() - origine.y())
        self._borner()
        self.update()

    def mouseReleaseEvent(self, event) -> None:      # noqa: N802 -- nom Qt
        self._depart_glisse = None
        self.unsetCursor()

    def nativeGestureEvent(self, event) -> bool:     # noqa: N802 -- nom Qt
        """Le pincement du pavé tactile, là où le système en émet.

        Le geste rend une échelle absolue depuis son début ; on la ramène à un
        facteur relatif pour la composer avec l'agrandissement en cours.
        """
        geste = event.gestureType()
        if geste == Qt.NativeGestureType.BeginNativeGesture:
            self._depart_pince = self._zoom
            return True
        if geste == Qt.NativeGestureType.ZoomNativeGesture:
            depart = self._depart_pince or self._zoom
            avant = self._zoom
            self._zoom = max(1.0, min(ZOOM_MAX, depart * (1.0 + event.value())))
            if avant > 0:
                rapport = self._zoom / avant
                self._glissement[0] *= rapport
                self._glissement[1] *= rapport
            self._borner()
            self.update()
            return True
        if geste == Qt.NativeGestureType.EndNativeGesture:
            self._depart_pince = None
            return True
        return False

    def resizeEvent(self, event) -> None:            # noqa: N802 -- nom Qt
        self._borner()
        super().resizeEvent(event)
