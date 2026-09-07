"""La liste déroulante des sélecteurs, à la largeur de ce qu'elle montre.

**Pourquoi ne pas se contenter d'un `QComboBox`.** Qt le taille sur le plus
long élément de toute la liste : le sélecteur d'entité s'étalait sur deux cent
trente pixels pour afficher « Koii (atys) », parce qu'une guilde au nom long
dormait plus bas dans la liste. La `Gtk.DropDown` de la version GTK se règle,
elle, sur l'élément **affiché** — et les deux sélecteurs de la barre n'y ont
pas la même largeur, chacun tenant à son texte.

`AdjustToContents` ne suffit pas : « le contenu » y désigne la liste entière,
pas la ligne visible. Il faut donc redire à Qt ce qu'est la largeur voulue.
"""
from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QComboBox


class Deroulante(QComboBox):
    """Une liste déroulante large de son seul texte courant."""

    def __init__(self, *arguments, **nommes) -> None:
        super().__init__(*arguments, **nommes)
        # **Le signal, et non la seule methode surchargee.** Un choix fait a
        # la souris pose l'index depuis le C++ de Qt : `setCurrentIndex` en
        # Python n'est alors jamais appele, et le selecteur gardait la largeur
        # de l'entite precedente -- « La Lune Eternelle » s'affichait
        # « La Lu » apres qu'on l'eut choisie dans la liste, alors que la
        # meme selection faite par le code passait sans encombre. Le signal,
        # lui, part quel que soit le chemin.
        self.currentIndexChanged.connect(self.updateGeometry)
        self.currentTextChanged.connect(self.updateGeometry)

    def sizeHint(self) -> QSize:                      # noqa: N802 -- nom Qt
        base = super().sizeHint()
        return QSize(self._largeur_du_texte(), base.height())

    def minimumSizeHint(self) -> QSize:               # noqa: N802 -- nom Qt
        base = super().minimumSizeHint()
        return QSize(min(self._largeur_du_texte(), base.width()),
                     base.height())

    def _largeur_du_texte(self) -> int:
        """Le texte affiché, plus la place du chevron et des marges.

        Les vingt-deux pixels sont ceux que la feuille donne au `drop-down`, et
        les seize le remplissage gauche et droite. Ils y sont écrits une fois ;
        les rappeler ici est le prix d'une largeur qui suit la police au lieu
        d'un nombre en dur.

        Les huit derniers sont l'air que GTK laisse entre le texte et son
        chevron : sans eux la parenthèse fermante vient toucher la flèche, et
        le nom paraît coupé alors qu'il est entier. Ils s'ajoutent à la
        largeur demandée — les prendre sur le remplissage rognerait le texte,
        puisque Qt réserve la zone du chevron en plus, et non dedans.
        """
        large = self.fontMetrics().horizontalAdvance(self.currentText()) + 46
        # Et l'image, quand la ligne en porte une : l'emblème de la guilde ou
        # le portrait du personnage. Sans la compter, la place lui était prise
        # sur le nom — « Koii » s'affichait « K » le jour où le portrait est
        # arrivé. Quatre pixels d'écart entre l'image et le texte, comme Qt en
        # laisse.
        if not self.itemIcon(self.currentIndex()).isNull():
            large += self.iconSize().width() + 4
        return large

    def showPopup(self) -> None:                      # noqa: N802 -- nom Qt
        """La liste ouverte prend la largeur de son plus long nom.

        Le champ ferme, lui, se regle sur la seule ligne affichee — c'est tout
        l'objet de cette classe. Mais la liste deroulante heritait de cette
        largeur-la, et coupait les noms plus longs que celui en cours : une
        guilde au nom de trente signes s'y lisait a moitie. La `Gtk.DropDown`
        de la version GTK ouvre sa liste a la largeur du plus long ; on fait
        de meme, en ajoutant de quoi loger la bordure et l'ascenseur.
        """
        metriques = self.view().fontMetrics()
        plus_long = max((metriques.horizontalAdvance(self.itemText(rang))
                         for rang in range(self.count())), default=0)
        self.view().setMinimumWidth(plus_long + 34)
        super().showPopup()

    def setItemText(self, index: int, texte: str) -> None:   # noqa: N802
        """Renommer l'element affiche change aussi la largeur voulue."""
        super().setItemText(index, texte)
        if index == self.currentIndex():
            self.updateGeometry()
