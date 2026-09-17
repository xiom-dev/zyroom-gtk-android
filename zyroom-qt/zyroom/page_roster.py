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

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                               QMenu, QPushButton, QScrollArea, QVBoxLayout,
                               QWidget)

from . import roster
from . import theme
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
    ("grade", False): ("▼", "tri-retro", "rétrogradation"),
}


def _norm(texte: str) -> str:
    import unicodedata
    texte = unicodedata.normalize("NFKD", texte)
    return "".join(c for c in texte if not unicodedata.combining(c)).lower()


def _signe(changement) -> tuple:
    if changement.kind == "grade":
        return SIGNES[("grade", changement.promotion)]
    return SIGNES[(changement.kind, True)]


class _Rangee(QWidget):
    """Une rangée du registre. Elle dit quand on la clique et qu'on la survole.

    **Plusieurs lignes d'un coup.** Chaque étiquette se sélectionnait déjà à la
    souris, mais une par une : recopier trois arrivées dans le canal de guilde
    demandait trois passages. Qt n'a rien d'équivalent au `SelectionMode` d'une
    `Gtk.ListBox` pour une pile de widgets — clic, Maj+clic, Ctrl+clic et
    glissé se posent donc ici, et la page en tient le compte.
    """

    clique = Signal(int, Qt.KeyboardModifier)
    glissee = Signal(int, QPoint)
    appelee = Signal(int, QPoint)

    def __init__(self, rang: int) -> None:
        super().__init__()
        self._rang = rang
        # Sans cet attribut, Qt ne peint pas le fond que la feuille de style
        # donne a un QWidget nu.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def mousePressEvent(self, evenement) -> None:      # noqa: N802
        if evenement.button() == Qt.MouseButton.RightButton:
            self.appelee.emit(self._rang, evenement.globalPosition().toPoint())
            return
        if evenement.button() == Qt.MouseButton.LeftButton:
            self.clique.emit(self._rang, evenement.modifiers())
        super().mousePressEvent(evenement)

    def mouseMoveEvent(self, evenement) -> None:       # noqa: N802
        """Le glissé. **Toujours reçu par la rangée où le bouton s'est
        enfoncé** : Qt lui donne la souris jusqu'au relâchement, et les
        coordonnées sortent d'elle. On passe donc le point en repère écran, et
        c'est la page qui dit quelle rangée se trouve dessous.
        """
        if evenement.buttons() & Qt.MouseButton.LeftButton:
            self.glissee.emit(self._rang,
                              evenement.globalPosition().toPoint())
        super().mouseMoveEvent(evenement)


class PageEffectif(QWidget):
    def __init__(self, fenetre) -> None:
        super().__init__()
        self._fenetre = fenetre
        self._vue = "effectif"
        #: Les rangees affichees, leur choix, et le point d'ou part une plage
        #: tenue a Maj+clic.
        self._rangees: list = []
        self._choisies: set = set()
        self._ancre = None
        copier = QShortcut(QKeySequence.StandardKey.Copy, self)
        # Sur la page et non sur la fenetre : le journal des mouvements a son
        # propre Ctrl+C, et deux raccourcis identiques sur la meme fenetre se
        # disputeraient la frappe.
        copier.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        copier.activated.connect(self._copier_choix)

        colonne = QVBoxLayout(self)
        colonne.setContentsMargins(0, 0, 0, 0)
        colonne.setSpacing(4)

        barre = QWidget()
        ligne = QHBoxLayout(barre)
        # Quatre en bas, et non zero : avec les quatre d'ecart de la
        # colonne, cela fait les huit pixels d'air que GTK pose sous
        # chacune de ses barres de filtres.
        ligne.setContentsMargins(8, 8, 8, 4)
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
        for rang, (nom, etiquette) in enumerate(
                (("effectif", _("Effectif")),
                 ("mouvements", _("Arrivées et départs")))):
            bouton = QPushButton(etiquette)
            bouton.setCheckable(True)
            # `lie` et non `nav` : ce sont deux bascules collees, pas les
            # onglets de la barre du haut, et elles n'en ont pas la hauteur.
            bouton.setObjectName("lie")
            bouton.setProperty("rang", "premier" if rang == 0 else "dernier")
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
        theme.poser_loupe(self._recherche)
        self._recherche.setClearButtonEnabled(True)
        self._recherche.textChanged.connect(self.rafraichir)
        self._recherche.setMinimumWidth(240)
        # **Il prend toute la place qui reste**, comme le `hexpand` de son
        # jumeau GTK : il faisait deux cent quarante pixels quand celui de GTK
        # en fait six cent quatre-vingt-quinze, et l'on cherchait un nom dans
        # une fente.
        ligne.addWidget(self._recherche, 1)

        self._statut = QLabel()
        self._statut.setObjectName("discret")
        ligne.addWidget(self._statut)
        # **Un ressort pour finir la ligne.** Le champ de recherche s'efface
        # quand on passe aux mouvements -- il ne filtrerait rien -- et la
        # place qu'il libere allait aux deux bascules, qui s'elargissaient
        # d'un coup sous le pointeur. Ce ressort la prend a leur place.
        #
        # Sans poids : il ne prend rien tant que le champ est la -- celui-ci a
        # le sien --, et ne retient la place que lorsque le champ s'efface.
        ligne.addStretch(0)
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
        """Fige la largeur des deux bascules sur leur libellé le plus long.

        **A rappeler une fois la feuille de style posee.** Une `QFontMetrics`
        prise au montage mesure la police par defaut de Qt -- neuf points --
        et non les onze de la feuille : la reservation tombait un cinquieme
        trop courte, et les boutons s'elargissaient quand meme a l'arrivee du
        registre. Le meme piege que la largeur du bouton d'ordre et que la
        chasse fixe du journal ; c'est `fenetre.py` qui rappelle celle-ci au
        bon moment.
        """
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
        self._oublier_choix()
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
    def _copiable(lbl: QLabel) -> QLabel:
        """Rend un libellé sélectionnable à la souris, et le rend.

        **Un nom de joueur se recopie.** Il part dans le canal de guilde ou
        dans un message, et le retaper de mémoire est le plus sûr moyen
        d'écorcher un pseudo. Comme la ligne de saison et le message de guilde,
        qui le sont déjà des deux côtés.
        """
        lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        return lbl

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

            entete = self._copiable(
                QLabel(f"{roster.nom_grade(grade)} · {len(noms)}"))
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
                    lbl = self._copiable(QLabel(nom))
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
            rangee = _Rangee(rang)
            self._brancher_rangee(rangee)
            if rang % 2 == 0:
                rangee.setProperty("zebre", True)
            ligne = QHBoxLayout(rangee)
            ligne.setContentsMargins(8, 2, 8, 2)
            ligne.setSpacing(8)

            # **Plus de `_copiable` ici.** Une etiquette selectionnable
            # avale le clic pour y poser un curseur de texte, et la ligne ne
            # se choisissait plus. Ce qu'on vient chercher -- le nom du
            # joueur -- part maintenant avec la ligne entiere.
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

    # ------------------------------------- Choisir et copier dans le registre
    def _oublier_choix(self) -> None:
        """Les rangs designeraient d'autres lignes une fois la liste refaite."""
        self._rangees = []
        self._choisies = set()
        self._ancre = None

    def _rangee_a(self, point_ecran: QPoint):
        """Le rang de la rangée sous ce point de l'écran, ou None."""
        for rang, rangee in enumerate(self._rangees):
            haut = rangee.mapToGlobal(rangee.rect().topLeft()).y()
            if haut <= point_ecran.y() < haut + rangee.height():
                return rang
        return None

    def _on_rangee_cliquee(self, rang: int, modificateurs) -> None:
        """Choisit une ligne, une plage avec Maj, ou en ajoute une avec Ctrl."""
        avant = set(self._choisies)
        if (modificateurs & Qt.KeyboardModifier.ShiftModifier
                and self._ancre is not None):
            debut, fin = sorted((self._ancre, rang))
            self._choisies = set(range(debut, fin + 1))
        elif modificateurs & Qt.KeyboardModifier.ControlModifier:
            self._choisies ^= {rang}
            self._ancre = rang
        else:
            self._choisies = {rang}
            self._ancre = rang
        self._maj_surlignage(avant)

    def _on_rangee_glissee(self, _rang: int, point_ecran: QPoint) -> None:
        """Étend le choix jusqu'à la rangée sous le pointeur."""
        if self._ancre is None:
            return
        arrivee = self._rangee_a(point_ecran)
        if arrivee is None:
            return
        avant = set(self._choisies)
        debut, fin = sorted((self._ancre, arrivee))
        self._choisies = set(range(debut, fin + 1))
        if self._choisies != avant:
            self._maj_surlignage(avant)

    def _maj_surlignage(self, avant: set = frozenset()) -> None:
        """Repeint les seules rangées dont l'état a changé."""
        for rang in set(avant) ^ self._choisies:
            if rang >= len(self._rangees):
                continue
            rangee = self._rangees[rang]
            rangee.setProperty("choisie", rang in self._choisies)
            rangee.style().unpolish(rangee)
            rangee.style().polish(rangee)

    def _lignes_choisies(self) -> list:
        """Le texte des rangées choisies, de haut en bas."""
        textes = []
        for rang in sorted(self._choisies):
            if rang >= len(self._rangees):
                continue
            mots = [lbl.text() for lbl in
                    self._rangees[rang].findChildren(QLabel) if lbl.text()]
            if mots:
                textes.append("  ".join(mots))
        return textes

    def _copier_choix(self) -> None:
        """Ctrl+C : met les rangées choisies dans le presse-papiers."""
        textes = self._lignes_choisies()
        if not textes:
            return
        QGuiApplication.clipboard().setText("\n".join(textes))
        self._statut.setText(_("%d ligne(s) copiée(s).") % len(textes))

    def _on_rangee_appelee(self, rang: int, point_ecran: QPoint) -> None:
        """Propose de copier ce qui est choisi, ou la rangée visée."""
        # Un clic droit hors de ce qui est choisi prend la rangee visee : sinon
        # le menu proposerait de copier des lignes qu'on ne montre pas du
        # doigt.
        if rang not in self._choisies:
            avant = set(self._choisies)
            self._choisies = {rang}
            self._ancre = rang
            self._maj_surlignage(avant)
        textes = self._lignes_choisies()
        if not textes:
            return
        menu = QMenu(self)
        action = menu.addAction(_("Copier la ligne") if len(textes) == 1
                                else _("Copier les %d lignes") % len(textes))
        action.triggered.connect(self._copier_choix)
        menu.exec(point_ecran)

    def _brancher_rangee(self, rangee) -> None:
        """Relie une rangée neuve au choix, et la retient."""
        rangee.clique.connect(self._on_rangee_cliquee)
        rangee.glissee.connect(self._on_rangee_glissee)
        rangee.appelee.connect(self._on_rangee_appelee)
        self._rangees.append(rangee)

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
