"""L'arbre des compétences : quatre branches qui se plient à tous les échelons.

Chaque ligne porte son niveau et l'avancement du niveau en cours. Ce qui est
monté au maximum passe au vert — c'est ce qui se voit de loin en faisant
défiler.

**L'arbre s'ouvre quelle que soit l'entité choisie** : c'est celui du dernier
personnage rencontré. Une guilde n'a pas de compétences, et devoir rebasculer
d'entité pour consulter un arbre n'aurait aucun sens.
"""
from __future__ import annotations

import unicodedata

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QLineEdit,
                               QProgressBar, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget)

from . import skills as skills_mod
from . import theme
from .i18n import _
from .ryzom_api import KIND_CHARACTER


def _norm(texte: str) -> str:
    texte = unicodedata.normalize("NFKD", texte)
    return "".join(c for c in texte if not unicodedata.combining(c)).lower()


class _Rangee(QWidget):
    """Une ligne de l'arbre. Elle previent quand on la clique.

    GTK a `row-activated` sur sa ListBox ; en Qt, une ligne faite de widgets
    n'est pas cliquable d'elle-meme -- on ajoute donc le signal qui manque.
    """

    clique = Signal(str)

    def __init__(self, code: str) -> None:
        super().__init__()
        self._code = code
        # Sans cet attribut, un widget d'une classe a soi ignore le
        # `background-color` de la feuille de style : Qt ne peint le fond que
        # des widgets qu'il connait. Le zebrage des lignes ne paraissait pas,
        # alors que la meme regle teintait bien l'effectif -- fait de QWidget
        # ordinaires, eux.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        if code:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, event) -> None:   # noqa: N802 -- nom impose
        if self._code:
            self.clique.emit(self._code)
        super().mouseReleaseEvent(event)


class PageCompetences(QWidget):
    def __init__(self, fenetre) -> None:
        super().__init__()
        self._fenetre = fenetre
        self._deplies: set[str] = set()
        self._finies: set[str] = set()
        self._arbre: list = []
        self._de = ""

        colonne = QVBoxLayout(self)
        colonne.setContentsMargins(0, 0, 0, 0)
        colonne.setSpacing(4)

        barre = QWidget()
        ligne = QHBoxLayout(barre)
        ligne.setContentsMargins(8, 8, 8, 0)
        ligne.setSpacing(8)

        self._recherche = QLineEdit()
        self._recherche.setPlaceholderText(_("Rechercher une compétence…"))
        self._recherche.setClearButtonEnabled(True)
        self._recherche.textChanged.connect(self.rafraichir)
        ligne.addWidget(self._recherche, 1)

        self._dd_filtre = QComboBox()
        self._dd_filtre.addItems([_("Tout"), _("En cours")])
        self._dd_filtre.setToolTip(
            _("« En cours » ne garde que les niveaux entamés"))
        self._dd_filtre.currentIndexChanged.connect(self.rafraichir)
        ligne.addWidget(self._dd_filtre)

        # Un seul bouton : son nom dit ce qu'il va faire, et il n'y a jamais
        # qu'une action sensee a proposer.
        self._btn_plier = QPushButton(_("Tout déplier"))
        self._btn_plier.clicked.connect(self._tout_basculer)
        ligne.addWidget(self._btn_plier)
        colonne.addWidget(barre)

        self._contenu = QWidget()
        self._liste = QVBoxLayout(self._contenu)
        self._liste.setContentsMargins(0, 0, 0, 0)
        self._liste.setSpacing(0)
        defilant = QScrollArea()
        defilant.setWidget(self._contenu)
        defilant.setWidgetResizable(True)
        colonne.addWidget(defilant, 1)

        self._statut = QLabel()
        self._statut.setObjectName("discret")
        self._statut.setContentsMargins(8, 0, 8, 6)
        colonne.addWidget(self._statut)

    # ------------------------------------------------------------ Actions
    def _tout_basculer(self) -> None:
        if self._deplies:
            self._deplies = set()
        else:
            self._deplies = {n.skill.code for n in self._arbre if n.has_children}
        self.rafraichir()

    def _basculer(self, code: str) -> None:
        if code in self._deplies:
            self._deplies.discard(code)
        else:
            self._deplies.add(code)
        self.rafraichir()

    def _vider(self) -> None:
        while self._liste.count():
            element = self._liste.takeAt(0)
            if element.widget():
                element.widget().deleteLater()

    # ----------------------------------------------------------- Affichage
    def rafraichir(self) -> None:
        """Redessine l'arbre.

        Ce qui est visible dépend des replis, sauf quand une recherche ou un
        filtre est actif — la liste est alors plate, car chercher « épée » et
        ne rien voir parce que la branche est fermée serait absurde.
        """
        self._vider()

        ent = self._fenetre.entite
        ailleurs = False
        if not getattr(ent, "skills", None):
            ent = (self._fenetre.dernier_perso
                   or self._fenetre.entite_en_cache(KIND_CHARACTER))
            if self._fenetre.dernier_perso is None:
                self._fenetre.dernier_perso = ent
            ailleurs = ent is not None
        competences = getattr(ent, "skills", []) if ent else []

        if not competences:
            self._statut.setText(
                _("Aucun personnage consulté pour l'instant : ouvrez-en un une "
                  "fois, et son arbre restera consultable d'ici. L'API ne "
                  "donne les compétences que pour un personnage, et seulement "
                  "si la clé accorde ce module."))
            self._btn_plier.setEnabled(False)
            self._liste.addStretch(1)
            return

        self._btn_plier.setEnabled(True)
        self._de = ent.name if ailleurs else ""
        self._entite = ent

        self._arbre = skills_mod.build_tree(competences)
        # Ce qui est monte au maximum, y compris les peres dont tout ce qu'ils
        # portent est fini : c'est ce qu'on cherche en parcourant l'arbre.
        self._finies = skills_mod.finished(self._arbre)

        motif = _norm(self._recherche.text().strip())
        en_cours = self._dd_filtre.currentIndex() == 1
        filtre = bool(motif) or en_cours

        noms = self._fenetre.noms
        if filtre:
            rangees = [n for n in self._arbre
                       if (not en_cours or n.skill.progress)
                       and (not motif
                            or motif in _norm(noms.name(n.skill.code)))]
        else:
            rangees = skills_mod.visible(self._arbre, self._deplies)

        self._btn_plier.setText(_("Tout replier") if self._deplies
                                else _("Tout déplier"))
        self._btn_plier.setVisible(not filtre)

        for index, noeud in enumerate(rangees):
            self._liste.addWidget(self._rangee(noeud, index, filtre))
        self._liste.addStretch(1)

        # Le nom du personnage n'est rappele que si ce n'est pas celui qu'on
        # regarde : sinon il serait deja deux fois a l'ecran.
        prefixe = f"{self._de} · " if self._de else ""
        self._statut.setText(prefixe + _("%d compétences, %d affichées")
                             % (len(competences), len(rangees)))

    def _rangee(self, noeud, index: int, filtre: bool) -> QWidget:
        racine = noeud.depth == 0 and not filtre
        code = noeud.skill.code if (noeud.has_children and not filtre) else ""
        rangee = _Rangee(code)
        rangee.clique.connect(self._basculer)
        # Une ligne sur deux teintee, comme les tableaux de l'application
        # Android : sur des colonnes etroites l'oeil perd sa ligne.
        if index % 2 == 0:
            rangee.setProperty("zebre", True)

        colonne = QVBoxLayout(rangee)
        colonne.setContentsMargins(0, 0, 0, 0)
        colonne.setSpacing(0)

        corps = QWidget()
        ligne = QHBoxLayout(corps)
        # Un cran par echelon, a partir du retrait de la fleche des racines.
        ligne.setContentsMargins(8 + (0 if filtre else noeud.depth * 14),
                                 4, 8, 4)
        ligne.setSpacing(6)

        fleche = QLabel(("▾" if noeud.skill.code in self._deplies else "▸")
                        if code else " ")
        fleche.setFixedWidth(theme.largeur(fleche, 0.75))
        ligne.addWidget(fleche)

        finie = noeud.skill.code in self._finies
        nom = QLabel(self._fenetre.noms.name(noeud.skill.code))
        if finie:
            # Toute la ligne au vert quand il n'y a plus rien a monter : c'est
            # ce qui se voit de loin en faisant defiler, et le pere compte
            # autant que sa feuille.
            nom.setObjectName("fini")
        elif racine:
            nom.setObjectName("titre")
        ligne.addWidget(nom, 1)

        if noeud.skill.progress:
            barre = QProgressBar()
            barre.setRange(0, 100)
            barre.setValue(noeud.skill.progress)
            barre.setTextVisible(False)
            barre.setFixedWidth(theme.largeur(barre, 4.7))
            ligne.addWidget(barre)

        # Le niveau atteint, et non le plafond de l'echelon : "Creer bijoux"
        # affichait 50 quand tout ce qu'elle porte est monte a 250, et il
        # fallait deplier pour le savoir.
        atteint = (skills_mod.niveau_atteint(self._arbre, noeud.skill.code)
                   if noeud.has_children else noeud.skill.level)
        texte_niveau = (f"{atteint} · {noeud.skill.progress} %"
                        if noeud.skill.progress else str(atteint))
        points = None
        if racine:
            points = getattr(self._entite, "skill_points", {}).get(
                noeud.skill.code)
        niveau = QLabel(texte_niveau)
        # Assez large pour « 250 · 99 % » : a 4,7 hauteurs de ligne, les
        # centaines se faisaient couper -- « 128 · 38 % » s'affichait
        # « 28 · 38 % », et le niveau devenait faux a la lecture.
        niveau.setFixedWidth(theme.largeur(niveau, 6.2))
        niveau.setAlignment(Qt.AlignmentFlag.AlignRight
                            | Qt.AlignmentFlag.AlignVCenter)
        if finie:
            niveau.setObjectName("fini")
        ligne.addWidget(niveau)
        colonne.addWidget(corps)

        if racine and points:
            detail = QLabel(_("%s pts · %s dépensés")
                            % (f"{points[0]:,}".replace(",", " "),
                               f"{points[1]:,}".replace(",", " ")))
            detail.setObjectName("discret")
            detail.setContentsMargins(8 + 14, 0, 8, 4)
            colonne.addWidget(detail)
        return rangee
