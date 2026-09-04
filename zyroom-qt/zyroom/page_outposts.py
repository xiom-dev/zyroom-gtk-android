"""Qui tient quoi sur Atys, et le journal des prises.

L'annuaire public des guildes ne demande aucune clé, mais pèse un demi-
mégaoctet : il n'est donc demandé qu'à l'ouverture de l'onglet, et rafraîchi à
la main.

Comme pour l'effectif, **l'API ne garde aucune histoire** : elle dit qui tient
quoi maintenant. Les changements de main se déduisent d'un relevé à l'autre, et
c'est `outposts.py`, dans le noyau partagé, qui tient ce journal.
"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics, QPixmap
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QStackedWidget, QVBoxLayout,
                               QWidget)

from . import outposts, ryzom_api
from . import theme
from .i18n import _
from .ryzom_api import KIND_GUILD

#: Les quatre peuples, dans l'ordre de la carte.
PEUPLES = (("fyros", "Fyros"), ("matis", "Matis"),
           ("tryker", "Tryker"), ("zorai", "Zoraï"))

#: La part de la taille des icones d'inventaire qu'occupe un embleme.
PART_EMBLEME = 0.42

#: Largeur du bloc des trois colonnes. Le nom tenait autrefois toute la
#: largeur disponible, ce qui repoussait le niveau et la guilde contre le bord
#: droit : sur un ecran large, l'oeil devait traverser vingt centimetres de
#: vide pour relier un avant-poste a son proprietaire.
LARGEUR_BLOC = 456

#: Les trois colonnes du bloc. Des largeurs fixes plutot que le `SizeGroup` de
#: GTK, qui n'a pas d'equivalent en Qt : sans elles, un nom long repousserait
#: le niveau et la guilde, et aucune colonne ne serait alignee d'une ligne a
#: l'autre.
LARGEUR_NOM = 240
LARGEUR_GUILDE = 150


class PageAvantPostes(QWidget):
    def __init__(self, fenetre) -> None:
        super().__init__()
        self._fenetre = fenetre
        self._carte: list = []
        self._changements: list = []
        self._premier = False
        self._charge = False

        colonne = QVBoxLayout(self)
        colonne.setContentsMargins(0, 0, 0, 0)
        colonne.setSpacing(4)

        barre = QWidget()
        ligne = QHBoxLayout(barre)
        ligne.setContentsMargins(8, 8, 8, 0)
        ligne.setSpacing(8)

        self._dd_vue = QComboBox()
        self._dd_vue.addItems([_("Qui tient quoi"), _("Journal des prises")])
        self._dd_vue.currentIndexChanged.connect(self._rafraichir)
        ligne.addWidget(self._dd_vue)

        self._btn_actualiser = QPushButton(_("Actualiser"))
        self._btn_actualiser.setToolTip(_("Redemander l'annuaire des guildes"))
        self._btn_actualiser.clicked.connect(lambda: self.charger(force=True))
        ligne.addWidget(self._btn_actualiser)

        self._statut = QLabel()
        self._statut.setObjectName("discret")
        ligne.addWidget(self._statut, 1)
        colonne.addWidget(barre)

        # Deux colonnes : Fyros et Matis a gauche, Tryker et Zorai a droite.
        # Les vingt-neuf avant-postes tenaient sur une colonne plus haute que
        # l'ecran, et il fallait defiler pour comparer deux peuples. Chacune
        # defile pour son compte, les quatre listes n'ayant pas la meme
        # longueur.
        colonnes = QWidget()
        duo = QHBoxLayout(colonnes)
        duo.setContentsMargins(0, 0, 0, 0)
        duo.setSpacing(12)
        self._gauche, defil_g = self._colonne_defilante()
        self._droite, defil_d = self._colonne_defilante()
        duo.addWidget(defil_g, 1)
        duo.addWidget(defil_d, 1)

        # Le journal, lui, se lit sur toute la largeur : ses lignes sont des
        # phrases, pas un tableau.
        self._journal, defil_j = self._colonne_defilante()

        self._pile = QStackedWidget()
        self._pile.addWidget(colonnes)      # 0 : la carte
        self._pile.addWidget(defil_j)       # 1 : le journal
        colonne.addWidget(self._pile, 1)

    @staticmethod
    def _colonne_defilante() -> tuple[QVBoxLayout, QScrollArea]:
        contenu = QWidget()
        pile = QVBoxLayout(contenu)
        pile.setContentsMargins(0, 0, 0, 0)
        pile.setSpacing(0)
        defilant = QScrollArea()
        defilant.setWidget(contenu)
        defilant.setWidgetResizable(True)
        defilant.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        return pile, defilant

    # -------------------------------------------------------- Chargement
    def charger(self, force: bool = False) -> None:
        """Va chercher l'annuaire, journalise les changements de main."""
        if self._charge and not force:
            # L'annuaire est deja en memoire : rien a redemander au reseau.
            # Mais l'entete et le surlignage vert disent "et nous ?", et le
            # "nous" a pu changer depuis -- sans ce rafraichissement,
            # l'affichage restait sur la guilde precedente.
            if self._carte:
                self._rafraichir()
            return
        self._charge = True
        self._btn_actualiser.setEnabled(False)
        self._statut.setText(_("Lecture de l'annuaire des guildes…"))
        magasin = self._fenetre.magasin_avant_postes

        def travail():
            xml = ryzom_api.fetch_guild_directory_xml()
            carte = outposts.parse_outposts(xml)
            premier = magasin.jamais_releve()
            magasin.record(carte)
            return carte, magasin.history(), premier

        def apres(resultat, erreur):
            self._btn_actualiser.setEnabled(True)
            if erreur:
                self._statut.setText(_("Annuaire indisponible : %s") % erreur)
                return
            self._carte, self._changements, self._premier = resultat
            self._statut.setText("")
            self._rafraichir()

        self._fenetre.passerelle.lancer(travail, apres)

    # ----------------------------------------------------------- Affichage
    @staticmethod
    def _vider(pile: QVBoxLayout) -> None:
        while pile.count():
            element = pile.takeAt(0)
            if element.widget():
                element.widget().deleteLater()

    def _rafraichir(self) -> None:
        for pile in (self._gauche, self._droite, self._journal):
            self._vider(pile)
        if not self._carte:
            return
        if self._dd_vue.currentIndex() == 1:
            self._pile.setCurrentIndex(1)
            self._remplir_journal()
            self._journal.addStretch(1)
        else:
            self._pile.setCurrentIndex(0)
            self._remplir_carte()
            self._gauche.addStretch(1)
            self._droite.addStretch(1)

    def _remplir_carte(self) -> None:
        carte = self._carte
        # Sur une guilde, c'est son nom ; sur un personnage, celui de sa
        # guilde. Sans cela, ouvrir la carte depuis son personnage ne mettait
        # rien en vert, alors que c'est justement la qu'on se demande
        # "et nous ?".
        ent = self._fenetre.entite
        ma_guilde = ""
        if ent is not None:
            ma_guilde = (ent.name if ent.kind == KIND_GUILD
                         else ent.guild) or ""
        miens = sum(1 for o in carte if o.guild == ma_guilde)
        entete = _("%d avant-postes tenus sur Atys") % len(carte)
        # Des qu'on sait de quelle guilde on parle, on le dit -- meme quand la
        # reponse est zero. Taire le compte nul laissait croire a un affichage
        # reste en arriere : « et nous ? » merite un « aucun » explicite.
        if ma_guilde:
            entete += _(", dont %d à %s") % (miens, ma_guilde)
        self._statut.setText(entete + ".")

        noms = self._fenetre.noms
        connus = {code for code, _n in PEUPLES}
        for pile, peuples in ((self._gauche, PEUPLES[:2]),
                              (self._droite, PEUPLES[2:])):
            rang = 0
            for code, nom in peuples:
                # Du plus haut niveau au plus bas, comme on lit une carte de
                # conquete : les enjeux d'abord.
                siens = sorted((o for o in carte if o.people == code),
                               key=lambda o: (-o.level, noms.name(o.name_key)))
                if not siens:
                    continue
                pile.addWidget(self._entete_peuple(nom))
                for avant_poste in siens:
                    pile.addWidget(self._ligne(avant_poste,
                                               avant_poste.guild == ma_guilde,
                                               rang % 2 == 0))
                    rang += 1

        orphelins = [o for o in carte if o.people not in connus]
        if orphelins:
            # L'annuaire contient parfois un code qui n'est pas un avant-poste
            # -- "#15". Le taire ferait un total qui ne tombe pas juste.
            self._droite.addWidget(self._ligne_simple(
                _("Hors carte : ") + ", ".join(f"{o.code} ({o.guild})"
                                               for o in orphelins), True))

    def _remplir_journal(self) -> None:
        if self._premier and not self._changements:
            self._journal.addWidget(self._ligne_simple(
                _("Premier relevé : rien à comparer. Les changements de main "
                  "apparaîtront à partir du prochain."), True))
            return
        if not self._changements:
            self._journal.addWidget(self._ligne_simple(
                _("Aucun changement de main depuis le premier relevé."), True))
            return
        noms = self._fenetre.noms
        for rang, c in enumerate(self._changements):
            quand = datetime.fromtimestamp(c.at).strftime("%d/%m %H:%M")
            nom = noms.name(f"{c.outpost}.outpost")
            if c.taken:
                texte = _("%s — pris par %s") % (nom, c.to)
            elif c.lost:
                texte = _("%s — perdu par %s") % (nom, c.frm)
            else:
                texte = _("%s — %s ▸ %s") % (nom, c.frm, c.to)
            self._journal.addWidget(
                self._ligne_simple(f"{quand}   {texte}", zebre=rang % 2 == 0))

    @staticmethod
    def _entete_peuple(nom: str) -> QWidget:
        lbl = QLabel(nom)
        lbl.setObjectName("peuple")
        lbl.setContentsMargins(0, 10, 0, 2)
        # Aligne sur le bloc des lignes, qui est centre : un titre reste
        # contre le bord gauche n'aurait plus rien coiffe.
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setMinimumWidth(LARGEUR_BLOC)
        return lbl

    def _ligne(self, avant_poste, mien: bool, zebre: bool) -> QWidget:
        rangee = QWidget()
        # Sans cet attribut, Qt ne peint pas le fond que la feuille
        # de style donne a un QWidget nu.
        rangee.setAttribute(
            Qt.WidgetAttribute.WA_StyledBackground, True)
        if zebre:
            rangee.setProperty("zebre", True)
        exterieur = QHBoxLayout(rangee)
        exterieur.setContentsMargins(0, 3, 0, 3)
        exterieur.addStretch(1)

        bloc = QWidget()
        bloc.setFixedWidth(LARGEUR_BLOC)
        ligne = QHBoxLayout(bloc)
        ligne.setContentsMargins(0, 0, 0, 0)
        ligne.setSpacing(8)

        # L'embleme de la guilde, charge en tache de fond et mis en cache.
        embleme = QLabel()
        cote = self._fenetre.reglages.icone(PART_EMBLEME)
        embleme.setFixedWidth(cote)
        self._fenetre.icones.demander_embleme(
            avant_poste.icon, self._rappel_embleme(embleme, cote))
        ligne.addWidget(embleme)

        nom = QLabel()
        nom.setObjectName("fini" if mien else "compact")
        nom.setFixedWidth(LARGEUR_NOM)
        # Coupe a la main : un QLabel de largeur fixe ne raccourcit pas son
        # texte, il le laisse deborder -- "Avant-Poste Diplomatique du
        # Croisement" chevauchait la colonne du niveau. GTK avait
        # `set_ellipsize` ; en Qt c'est a l'appelant de mesurer.
        nom.setText(QFontMetrics(nom.font()).elidedText(
            self._fenetre.noms.name(avant_poste.name_key),
            Qt.TextElideMode.ElideRight, LARGEUR_NOM))
        ligne.addWidget(nom)

        niveau = QLabel(str(avant_poste.level) if avant_poste.level else "—")
        niveau.setObjectName("discret")
        niveau.setFixedWidth(theme.largeur(niveau, 1.25))
        niveau.setAlignment(Qt.AlignmentFlag.AlignRight
                            | Qt.AlignmentFlag.AlignVCenter)
        ligne.addWidget(niveau)

        guilde = QLabel()
        guilde.setObjectName("fini" if mien else "compact")
        guilde.setText(QFontMetrics(guilde.font()).elidedText(
            avant_poste.guild, Qt.TextElideMode.ElideRight, LARGEUR_GUILDE))
        ligne.addWidget(guilde, 1)

        exterieur.addWidget(bloc)
        exterieur.addStretch(1)
        return rangee

    @staticmethod
    def _rappel_embleme(cible: QLabel, cote: int):
        def arrivee(chemin):
            if not chemin:
                return
            image = QPixmap(chemin)
            if not image.isNull():
                cible.setPixmap(image.scaledToWidth(
                    cote, Qt.TransformationMode.SmoothTransformation))
        return arrivee

    @staticmethod
    def _ligne_simple(texte: str, discret: bool = False,
                      zebre: bool = False) -> QWidget:
        lbl = QLabel(texte)
        lbl.setWordWrap(True)
        lbl.setContentsMargins(8, 4, 8, 4)
        if discret:
            lbl.setObjectName("discret")
        if zebre:
            lbl.setProperty("zebre", True)
        return lbl
