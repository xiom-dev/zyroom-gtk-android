"""Le registre du personnel d'une guilde : qui en est, qui arrive, qui part.

Deux vues sous un même onglet, comme les deux pastilles du téléphone :
l'effectif du jour, et le journal des arrivées et des départs.

**L'API ne garde aucune histoire.** Elle rend un effectif, celui de l'instant.
Les mouvements se déduisent en comparant deux relevés — c'est `roster.py`, dans
le noyau partagé, qui tient ce registre. Sans l'application, ces allées et
venues ne seraient enregistrées nulle part.

**L'écran s'ouvre quelle que soit l'entité choisie** : c'est le registre de la
dernière guilde rencontrée. Consulter un effectif ne devrait pas obliger à
changer d'entité ; le nom de la guilde est rappelé quand ce n'est pas celle
qu'on regarde.
"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QScrollArea, QVBoxLayout, QWidget)

from . import roster
from .config import data_dir
from .i18n import _
from .ryzom_api import KIND_GUILD

#: Le nombre de colonnes de noms. Cent soixante-dix noms sur une seule colonne
#: faisaient un ruban plus haut que dix ecrans, ou l'on ne trouvait rien.
COLONNES = 6

#: Le signe de chaque mouvement : forme, nom de style, et sens.
#:
#: La couleur porte le sens -- vert pour ce qui entre, rouge pour ce qui sort,
#: blanc pour ce qui bouge a l'interieur -- et la direction du triangle le
#: confirme, pour qui distingue mal les deux teintes.
SIGNES = {
    ("arrivee", True): ("▲", "tri-arrivee", "arrivée"),
    ("depart", True): ("▼", "tri-depart", "départ"),
    ("grade", True): ("▲", "tri-grade", "montée de grade"),
    ("grade", False): ("▼", "tri-grade", "rétrogradation"),
}


def _norm(texte: str) -> str:
    import unicodedata
    texte = unicodedata.normalize("NFKD", texte)
    return "".join(c for c in texte if not unicodedata.combining(c)).lower()


def _signe(changement) -> tuple:
    if changement.kind == "grade":
        return SIGNES[("grade", changement.promotion)]
    return SIGNES[(changement.kind, True)]


class PageEffectif(QWidget):
    def __init__(self, fenetre) -> None:
        super().__init__()
        self._fenetre = fenetre
        self._vue = "effectif"

        colonne = QVBoxLayout(self)
        colonne.setContentsMargins(0, 0, 0, 0)
        colonne.setSpacing(4)

        barre = QWidget()
        ligne = QHBoxLayout(barre)
        ligne.setContentsMargins(8, 8, 8, 0)
        ligne.setSpacing(8)

        # Deux bascules liees plutot qu'un menu deroulant. Le menu cachait la
        # seconde vue a qui ne pensait pas a le derouler -- et son premier
        # choix s'appelant "Effectif", du nom de la page elle-meme, rien ne
        # laissait deviner qu'il y avait autre chose dessous.
        vues = QWidget()
        ligne_vues = QHBoxLayout(vues)
        ligne_vues.setContentsMargins(0, 0, 0, 0)
        ligne_vues.setSpacing(0)
        self._boutons = {}
        for nom, etiquette in (("effectif", _("Effectif")),
                               ("mouvements", _("Arrivées et départs"))):
            bouton = QPushButton(etiquette)
            bouton.setCheckable(True)
            bouton.setObjectName("nav")
            bouton.clicked.connect(lambda _c, n=nom: self._changer_vue(n))
            self._boutons[nom] = bouton
            ligne_vues.addWidget(bouton)
        self._boutons["effectif"].setChecked(True)

        # **La place du compte est reservee des le depart.** Les deux
        # libelles gagnent un « · 178 » des que le registre est lu, et les
        # boutons s'elargissaient alors d'un coup sous le pointeur, poussant
        # leur voisin. On leur donne tout de suite la largeur qu'ils auront
        # une fois remplis -- quatre chiffres, de quoi tenir la plus grosse
        # guilde -- et plus rien ne bouge ensuite.
        self._reserver_largeur()
        ligne.addWidget(vues)

        # Cent soixante-douze noms sur six colonnes se cherchent encore a
        # l'oeil. Le champ ne parait que sur l'effectif : le journal se lit par
        # sa date, et un champ qui ne filtrerait rien serait pire qu'absent.
        self._recherche = QLineEdit()
        self._recherche.setPlaceholderText(_("Rechercher un membre…"))
        self._recherche.setClearButtonEnabled(True)
        self._recherche.textChanged.connect(self.rafraichir)
        self._recherche.setMinimumWidth(240)
        ligne.addWidget(self._recherche)

        self._statut = QLabel()
        self._statut.setObjectName("discret")
        ligne.addWidget(self._statut)
        # **Un ressort pour finir la ligne.** Le champ de recherche s'efface
        # quand on passe aux mouvements -- il ne filtrerait rien -- et la
        # place qu'il libere allait aux deux bascules, qui s'elargissaient
        # d'un coup sous le pointeur. Ce ressort la prend a leur place.
        ligne.addStretch(1)
        colonne.addWidget(barre)

        self._contenu = QWidget()
        self._liste = QVBoxLayout(self._contenu)
        self._liste.setContentsMargins(0, 0, 0, 0)
        self._liste.setSpacing(0)

        defilant = QScrollArea()
        defilant.setWidget(self._contenu)
        defilant.setWidgetResizable(True)
        defilant.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        colonne.addWidget(defilant, 1)

    def _reserver_largeur(self) -> None:
        """Fige la largeur des deux bascules sur leur libellé le plus long."""
        from PySide6.QtGui import QFontMetrics
        for nom, gabarit in (("effectif", _("Effectif · %d") % 9999),
                             ("mouvements",
                              _("Arrivées et départs · %d") % 9999)):
            bouton = self._boutons[nom]
            large = QFontMetrics(bouton.font()).horizontalAdvance(gabarit)
            # La marge du style par-dessus le texte : le QSS en pose vingt-huit
            # de chaque cote, on ajoute de quoi ne jamais serrer.
            bouton.setMinimumWidth(large + 36)

    # ----------------------------------------------------------- Vues
    def _changer_vue(self, nom: str) -> None:
        """Deux bascules qui se conduisent comme un choix unique.

        Un bouton bascule se relâche quand on le reclique : recliquer la vue
        déjà affichée la laisserait sans aucune des deux d'active, et la liste
        se viderait. On le remet enfoncé sans rien redessiner.
        """
        if nom == self._vue:
            self._boutons[nom].setChecked(True)
            return
        self._vue = nom
        for autre, bouton in self._boutons.items():
            bouton.setChecked(autre == nom)
        self.rafraichir()

    def _vider(self) -> None:
        while self._liste.count():
            element = self._liste.takeAt(0)
            if element.widget():
                element.widget().deleteLater()

    # ------------------------------------------------------ Contenu
    def rafraichir(self) -> None:
        self._vider()
        self._recherche.setVisible(self._vue == "effectif")

        ent = self._fenetre.entite
        if ent is None or ent.kind != KIND_GUILD or not ent.members:
            ent = (self._fenetre.derniere_guilde
                   or self._fenetre.entite_en_cache(KIND_GUILD))
            if self._fenetre.derniere_guilde is None:
                self._fenetre.derniere_guilde = ent
            ailleurs = ent is not None
        else:
            ailleurs = False

        if ent is None:
            self._compter(0, 0)
            self._statut.setText("")
            self._liste.addWidget(self._ligne_simple(
                _("Aucune guilde consultée pour l'instant : ouvrez-en une une "
                  "fois, et son effectif restera consultable d'ici."), True))
            self._liste.addStretch(1)
            return

        magasin = roster.RosterStore(data_dir(), ent.entity_id)
        changements = magasin.history()
        # Les nombres sont sur les boutons : c'est la qu'ils disent quelque
        # chose -- "il y a trois mouvements a voir" -- au lieu de compter ce
        # qu'on a deja sous les yeux.
        self._compter(len(ent.members), len(changements))

        morceaux = []
        if ailleurs:
            morceaux.append(ent.name)
        if self._vue == "mouvements":
            morceaux.append(_("journal des %d derniers jours")
                            % roster.RETENTION_JOURS)
        self._statut.setText(" · ".join(morceaux))

        if self._vue == "mouvements":
            self._remplir_mouvements(changements)
        else:
            self._remplir_effectif(ent)
        self._liste.addStretch(1)

    def _compter(self, membres: int, mouvements: int) -> None:
        """Inscrit les deux comptes sur les bascules.

        Zéro ne s'écrit pas : « Arrivées et départs · 0 » se lit comme un
        compte à vérifier, alors qu'il n'y a rien à aller voir.
        """
        self._boutons["effectif"].setText(
            _("Effectif · %d") % membres if membres else _("Effectif"))
        self._boutons["mouvements"].setText(
            _("Arrivées et départs · %d") % mouvements if mouvements
            else _("Arrivées et départs"))

    @staticmethod
    def _ligne_simple(texte: str, discret: bool = False) -> QWidget:
        lbl = QLabel(texte)
        lbl.setWordWrap(True)
        lbl.setContentsMargins(8, 8, 8, 8)
        if discret:
            lbl.setObjectName("discret")
        return lbl

    def _remplir_effectif(self, ent) -> None:
        """L'effectif, par grade, en autant de colonnes que la fenêtre en tient.

        **C'est le grade qui est teinté, non la ligne** : le zébrage sert ici à
        séparer les groupes, pas à suivre une ligne — un nom n'a rien à droite
        de lui qu'on doive relier.
        """
        # Le chef d'abord, les membres ensuite : on lit une liste de guilde par
        # le haut, et l'API la rend dans un ordre qui n'en est pas un.
        cherche = _norm(self._recherche.text().strip())
        membres = sorted((nm for nm in ent.members
                          if not cherche or cherche in _norm(nm[0])),
                         key=lambda nm: (roster.rang_grade(nm[1]),
                                         nm[0].lower()))
        if not membres:
            self._liste.addWidget(self._ligne_simple(
                _("Aucun membre de ce nom."), True))
            return

        par_grade: dict[str, list[str]] = {}
        for nom, grade, *_reste in membres:   # le reste, c'est la date d'entree
            par_grade.setdefault(grade, []).append(nom)

        for rang_groupe, (grade, noms) in enumerate(par_grade.items()):
            teinte = rang_groupe % 2 == 0

            entete = QLabel(f"{roster.nom_grade(grade)} · {len(noms)}")
            entete.setObjectName("peuple")
            entete.setContentsMargins(8, 10, 8, 2)
            if teinte:
                entete.setProperty("zebre", True)
            self._liste.addWidget(entete)

            for depart in range(0, len(noms), COLONNES):
                tranche = noms[depart:depart + COLONNES]
                rangee = QWidget()
                # Sans cet attribut, Qt ne peint pas le fond que la feuille
                # de style donne a un QWidget nu.
                rangee.setAttribute(
                    Qt.WidgetAttribute.WA_StyledBackground, True)
                if teinte:
                    rangee.setProperty("zebre", True)
                grille = QGridLayout(rangee)
                grille.setContentsMargins(8, 1, 8, 1)
                grille.setHorizontalSpacing(4)
                # La rangee est toujours remplie jusqu'a six, au besoin de
                # cases vides : sans cela, la derniere rangee d'un grade --
                # deux noms -- s'etalerait sur toute la largeur au lieu de
                # s'aligner sur celles du dessus.
                for colonne in range(COLONNES):
                    nom = tranche[colonne] if colonne < len(tranche) else ""
                    lbl = QLabel(nom)
                    lbl.setObjectName("compact")
                    grille.addWidget(lbl, 0, colonne)
                    grille.setColumnStretch(colonne, 1)
                self._liste.addWidget(rangee)

    def _remplir_mouvements(self, changements: list) -> None:
        self._liste.addWidget(self._legende())
        if not changements:
            self._liste.addWidget(self._ligne_simple(
                _("Aucun mouvement depuis le premier relevé. Le registre "
                  "compare l'effectif d'une synchronisation à l'autre : l'API "
                  "ne garde aucune histoire, seule l'application en tient "
                  "une."), True))
            return
        for rang, changement in enumerate(changements):
            rangee = QWidget()
            # Sans cet attribut, Qt ne peint pas le fond que la feuille
            # de style donne a un QWidget nu.
            rangee.setAttribute(
                Qt.WidgetAttribute.WA_StyledBackground, True)
            if rang % 2 == 0:
                rangee.setProperty("zebre", True)
            ligne = QHBoxLayout(rangee)
            ligne.setContentsMargins(8, 2, 8, 2)
            ligne.setSpacing(8)

            quand = QLabel(datetime.fromtimestamp(changement.at)
                           .strftime("%d/%m %H:%M"))
            quand.setObjectName("discret")
            ligne.addWidget(quand)

            forme, style, _sens = _signe(changement)
            triangle = QLabel(forme)
            triangle.setObjectName(style)
            ligne.addWidget(triangle)

            ligne.addWidget(QLabel(roster.decrire(changement)), 1)
            self._liste.addWidget(rangee)

    def _legende(self) -> QWidget:
        """Quatre signes et leur sens, en tête du journal.

        Sans elle, un triangle rouge vers le bas se lit comme une alarme plutôt
        que comme un départ.

        Elle porte aussi ce que les dates ne peuvent pas dire d'elles-mêmes :
        une arrivée est datée du jour où elle a eu lieu, l'API le sait ; un
        départ ne l'est que du relevé qui l'a constaté, faute que l'API en
        garde la moindre trace.
        """
        boite = QWidget()
        ligne = QHBoxLayout(boite)
        ligne.setContentsMargins(8, 8, 8, 8)
        ligne.setSpacing(14)
        for forme, style, sens in (SIGNES[("arrivee", True)],
                                   SIGNES[("depart", True)],
                                   SIGNES[("grade", True)],
                                   SIGNES[("grade", False)]):
            paire = QWidget()
            duo = QHBoxLayout(paire)
            duo.setContentsMargins(0, 0, 0, 0)
            duo.setSpacing(4)
            triangle = QLabel(forme)
            triangle.setObjectName(style)
            duo.addWidget(triangle)
            texte = QLabel(_(sens))
            texte.setObjectName("discret")
            duo.addWidget(texte)
            ligne.addWidget(paire)
        ligne.addStretch(1)
        note = QLabel(_("départs et grades : date du relevé"))
        note.setObjectName("discret")
        ligne.addWidget(note)
        return boite
