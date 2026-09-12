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
from math import ceil
from typing import NamedTuple

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QFontMetrics, QFontMetricsF, QPixmap
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QStackedWidget, QVBoxLayout,
                               QWidget)

from . import outposts, ryzom_api
from . import theme
from .deroulante import Choix
from .config import noter_erreur
from .i18n import _
from .ryzom_api import KIND_GUILD

#: Les quatre peuples, dans l'ordre de la carte.
PEUPLES = (("fyros", "Fyros"), ("matis", "Matis"),
           ("tryker", "Tryker"), ("zorai", "Zoraï"))

#: La part de la taille des icones d'inventaire qu'occupe un embleme.
PART_EMBLEME = 0.42

#: Largeur minimale du bloc des trois colonnes. Le nom tenait autrefois toute
#: la largeur disponible, ce qui repoussait le niveau et la guilde contre le
#: bord droit : sur un ecran large, l'oeil devait traverser vingt centimetres
#: de vide pour relier un avant-poste a son proprietaire. Au-dela de ce
#: plancher, c'est le contenu qui commande -- voir `_mesures`.
LARGEUR_BLOC = 456

#: L'air entre deux colonnes du bloc, et le nombre d'intervalles : l'embleme,
#: le nom, le niveau, la guilde.
ESPACEMENT = 8
INTERVALLES = 3

#: Ce que la colonne du nom garde toujours, meme dans une fenetre etroite :
#: sous cela, tous les noms s'abregent au meme moignon et la colonne ne dit
#: plus rien.
LARGEUR_NOM_MINI = 120

#: Le nom de guilde s'abrege au-dela de cette longueur, comme le
#: `set_max_width_chars(24)` de la version GTK.
CARACTERES_GUILDE = 24

#: De combien la fenetre doit changer de largeur pour qu'on refasse la carte.
#: Pas un pixel : l'ascenseur vertical qui apparait en vaut dix a lui seul, et
#: reconstruire a chaque pixel ferait osciller l'affichage sans fin.
SEUIL_REDIMENSION = 24


def _entier(avance: float) -> int:
    """Une largeur de texte arrondie **vers le haut**, plus un pixel d'air.

    `horizontalAdvance` d'un `QFontMetrics` rend un entier tronque, alors que
    `elidedText` compare a la largeur reelle : « Grave of The Fireflies »
    mesure 169,23 pixels, la colonne taillee pour lui en faisait 169, et le
    nom de guilde le plus long de chaque colonne partait en points de
    suspension -- tous les autres tenant, le defaut passait pour une fatalite
    de la place disponible. GTK, lui, demande sa largeur naturelle en flottant
    et n'y perd rien.
    """
    return ceil(avance) + 1


class Mesures(NamedTuple):
    """La largeur des trois colonnes d'une carte, et celle de leur bloc."""
    nom: int
    niveau: int
    guilde: int
    bloc: int


class PageAvantPostes(QWidget):
    def __init__(self, fenetre) -> None:
        super().__init__()
        self._fenetre = fenetre
        self._carte: list = []
        self._changements: list = []
        self._premier = False
        self._charge = False
        #: La largeur qu'avait la page au dernier remplissage de la carte.
        #: Les colonnes sont taillees pour cette largeur-la ; si elle change
        #: beaucoup, il faut les retailler. Voir `resizeEvent`.
        self._largeur_remplie = 0

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

        self._dd_vue = Choix()
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
        self._gauche, self._defil_gauche = self._colonne_defilante()
        self._droite, self._defil_droite = self._colonne_defilante()
        duo.addWidget(self._defil_gauche, 1)
        duo.addWidget(self._defil_droite, 1)

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
        # **Le fond d'une vue, et non celui de la fenetre.** GTK met ici une
        # `Gtk.ListBox`, qu'Adwaita pose sur `view_bg_color` -- le #172226 des
        # cartes. Qt laissait paraitre le #10171a de la fenetre : une ligne
        # sur deux tranchait deux fois plus que chez GTK, alors que la couleur
        # du zebrage, elle, etait deja la bonne. C'est le fond d'en dessous
        # qui differait, pas la bande. Le viewport aussi, sans quoi le bas de
        # la colonne -- sous la derniere ligne -- reste noir.
        contenu.setObjectName("liste")
        contenu.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        pile = QVBoxLayout(contenu)
        pile.setContentsMargins(0, 0, 0, 0)
        pile.setSpacing(0)
        defilant = QScrollArea()
        defilant.setWidget(contenu)
        defilant.viewport().setObjectName("liste")
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
        # Avant le retour anticipe : le compte se lit dans le journal, qui
        # existe meme quand la carte n'est pas encore chargee.
        self._maj_compteur_prises()
        if not self._carte:
            return
        if self._dd_vue.currentIndex() == 1:
            self._pile.setCurrentIndex(1)
            self._remplir_journal()
            self._journal.addStretch(1)
            # Lu : le compte tombe a zero, et l'entree reprend son nom nu.
            magasin = self._fenetre.magasin_avant_postes
            if magasin is not None:
                magasin.marquer_lu()
            self._maj_compteur_prises()
        else:
            self._pile.setCurrentIndex(0)
            self._remplir_carte()
            self._gauche.addStretch(1)
            self._droite.addStretch(1)

    def _ma_guilde(self) -> str:
        """Le nom de la guilde qu'on regarde — la sienne, ou celle du perso."""
        ent = self._fenetre.entite
        if ent is None:
            return ""
        return (ent.name if ent.kind == KIND_GUILD else ent.guild) or ""

    def _maj_compteur_prises(self) -> None:
        """Le nombre de prises qui nous concernent, sur l'entree du journal.

        **Un nombre dans la deroulante, et pas une colonne de plus.** Le
        journal des prises existait deja et ne se voyait pas : il fallait
        penser a l'ouvrir. Le compte s'efface des qu'on l'a lu -- c'est un
        rappel, pas un decompte.
        """
        magasin = self._fenetre.magasin_avant_postes
        if magasin is None:
            return
        titre = _("Journal des prises")
        n = magasin.non_lus(self._ma_guilde())
        if n:
            titre += f" ({n})"
        if self._dd_vue.itemText(1) != titre:
            self._dd_vue.setItemText(1, titre)

    def _remplir_carte(self) -> None:
        carte = self._carte
        # Sur une guilde, c'est son nom ; sur un personnage, celui de sa
        # guilde. Sans cela, ouvrir la carte depuis son personnage ne mettait
        # rien en vert, alors que c'est justement la qu'on se demande
        # "et nous ?".
        ma_guilde = self._ma_guilde()
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
        self._largeur_remplie = self.width()
        for pile, peuples, defilant in (
                (self._gauche, PEUPLES[:2], self._defil_gauche),
                (self._droite, PEUPLES[2:], self._defil_droite)):
            # **Un jeu de mesures par colonne d'ecran**, et non un seul pour
            # les quatre peuples : c'est ce que fait GTK, un jeu de
            # `SizeGroup` par cote. Les deux colonnes n'ont pas les memes
            # noms, et leur imposer une largeur commune gacherait la place de
            # l'une.
            codes = {code for code, _n in peuples}
            mesures = self._mesures([o for o in carte if o.people in codes],
                                    defilant)
            rang = 0
            for code, nom in peuples:
                # Du plus haut niveau au plus bas, comme on lit une carte de
                # conquete : les enjeux d'abord.
                siens = sorted((o for o in carte if o.people == code),
                               key=lambda o: (-o.level, noms.name(o.name_key)))
                if not siens:
                    continue
                pile.addWidget(self._entete_peuple(
                    nom, min(LARGEUR_BLOC, mesures.bloc)))
                for avant_poste in siens:
                    # **Une ligne qui casse ne doit pas emporter l'ecran.**
                    # Un joueur sous Windows n'avait plus qu'un titre de peuple
                    # et du vide : la construction s'arretait a la premiere
                    # ligne fautive, et l'exception partait sur une sortie
                    # qu'un paquet sans console n'affiche jamais. On note ce
                    # qui a casse, on montre que la ligne manque, et l'on
                    # continue -- vingt-huit avant-postes lisibles valent mieux
                    # qu'un ecran blanc.
                    try:
                        rangee = self._ligne(avant_poste,
                                             avant_poste.guild == ma_guilde,
                                             rang % 2 == 0, mesures)
                    except Exception as souci:           # noqa: BLE001
                        noter_erreur(
                            f"avant-poste {getattr(avant_poste, 'code', '?')}",
                            souci)
                        rangee = self._ligne_simple(
                            _("(ligne illisible — voir erreurs.log)"), True)
                    pile.addWidget(rangee)
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
    def _entete_peuple(nom: str, largeur: int) -> QWidget:
        """Le nom du peuple, pose comme GTK le pose.

        **Un bloc centre dont le texte tient a gauche**, et non un texte
        centre. GTK donne au libelle une largeur de 456 -- le plancher du bloc
        des lignes --, le centre dans la colonne et laisse son `xalign` a
        zero : le nom du peuple tombe donc au debut de ce bloc, pas au milieu
        de la colonne. Qt le centrait, et les quatre titres flottaient au
        milieu du vide au lieu de coiffer leurs lignes.
        """
        rangee = QWidget()
        exterieur = QHBoxLayout(rangee)
        exterieur.setContentsMargins(0, 10, 0, 2)
        exterieur.addStretch(1)
        lbl = QLabel(nom)
        lbl.setObjectName("peuple")
        lbl.setFixedWidth(largeur)
        lbl.setAlignment(Qt.AlignmentFlag.AlignLeft
                         | Qt.AlignmentFlag.AlignVCenter)
        exterieur.addWidget(lbl)
        exterieur.addStretch(1)
        return rangee

    @staticmethod
    def _police(objet: str) -> QFont:
        """La police dont un libelle de ce nom d'objet sera vraiment peint.

        **Pourquoi ce detour.** La taille du texte ne vient pas de
        `QApplication.setFont` mais de la feuille de style -- `theme.feuille`
        dit pourquoi. Un `QLabel` tout juste construit rend donc la police par
        defaut de Qt, neuf points, quand l'ecran en affiche treize : mesurer
        un texte avec elle, c'est le croire d'un bon tiers plus court qu'il
        n'est. C'est ce qui faisait rogner « 250 » dans la colonne des
        niveaux, et ce qui laissait un nom abrege pour deux cent quarante
        pixels en occuper deux cent cinquante-sept -- de quoi passer par
        dessus la colonne voisine.

        `ensurePolished` applique la feuille au libelle : sa police devient
        celle du rendu.
        """
        sonde = QLabel()
        sonde.setObjectName(objet)
        sonde.ensurePolished()
        return sonde.font()

    def _mesures(self, siens: list, defilant: QScrollArea) -> Mesures:
        """La largeur des trois colonnes : chacune celle de son plus large.

        Le pendant des `Gtk.SizeGroup` de la version GTK, qui imposent a tous
        leurs membres la largeur du plus grand -- Qt n'en a pas d'equivalent,
        le calcul se fait donc ici.

        **Le nom est l'elastique.** L'embleme, le niveau et la guilde sont
        dus : ce qui reste de la place offerte revient au nom, sans depasser
        ce que reclame le plus long ni descendre sous `LARGEUR_NOM_MINI`.
        """
        # **Une seule police pour les trois colonnes**, celle du rendu : les
        # trois libelles d'une ligne portent `#compact`, le niveau comme les
        # deux autres. Mesurer le niveau dans `#discret`, qui ne reduit pas
        # le corps, le donnait plus large qu'il ne se peint.
        m_texte = QFontMetricsF(self._police("compact"))

        niveaux = [str(o.level) if o.level else "—" for o in siens] or ["—"]
        # Deux pixels d'air : sans eux, le dernier chiffre touche la colonne
        # voisine des que la police s'arrondit.
        largeur_niveau = ceil(max(m_texte.horizontalAdvance(t)
                                  for t in niveaux)) + 2

        noms = self._fenetre.noms
        textes = [noms.name(o.name_key) for o in siens] or [""]
        nom_ideal = _entier(max(m_texte.horizontalAdvance(t) for t in textes))

        # Comme le `set_max_width_chars(24)` de GTK : au-dela, un nom de
        # guilde bavard mangerait la colonne du nom.
        guildes = [o.guild for o in siens] or [""]
        largeur_guilde = min(
            _entier(max(m_texte.horizontalAdvance(g) for g in guildes)),
            ceil(m_texte.averageCharWidth() * CARACTERES_GUILDE))

        cote = self._fenetre.reglages.icone(PART_EMBLEME)
        du = cote + INTERVALLES * ESPACEMENT + largeur_niveau + largeur_guilde
        # La place offerte est celle de la zone defilante. Elle vaut zero
        # tant que la fenetre n'est pas posee : on s'en tient alors au
        # plancher, et `resizeEvent` retaillera.
        offert = defilant.viewport().width() or LARGEUR_BLOC
        # **L'ascenseur est compte meme quand il ne se voit pas encore.** La
        # carte est plus haute que l'ecran neuf fois sur dix : il parait donc
        # une fois les lignes posees, et vole apres coup les dix pixels sur
        # lesquels le dernier nom de guilde comptait -- il s'en trouvait
        # rogne d'une lettre, sans meme les points de suspension qui
        # l'auraient dit.
        barre = defilant.verticalScrollBar()
        if not barre.isVisible():
            offert -= barre.sizeHint().width()
        largeur_nom = min(nom_ideal, max(offert - du, LARGEUR_NOM_MINI))
        bloc = du + largeur_nom
        if bloc < LARGEUR_BLOC <= offert:
            # Le plancher laisse du rab : il revient au nom, seul a savoir
            # quoi en faire -- un nom de plus s'affiche en entier.
            bloc = LARGEUR_BLOC
            largeur_nom = bloc - du
        return Mesures(largeur_nom, largeur_niveau, largeur_guilde, bloc)

    @staticmethod
    def _abreger(libelle: QLabel, texte: str, largeur: int) -> str:
        """Le texte coupe a la largeur de sa colonne, dans sa vraie police.

        Un `QLabel` de largeur fixe ne raccourcit pas son texte de lui-meme :
        GTK avait `set_ellipsize`, en Qt c'est a l'appelant de mesurer. Le
        `ensurePolished` est le meme detour que dans `_police` -- sans lui, la
        coupe est calculee sur une police plus petite que celle du rendu, et
        le texte deborde de la colonne au lieu d'y tenir.
        """
        libelle.ensurePolished()
        return QFontMetrics(libelle.font()).elidedText(
            texte, Qt.TextElideMode.ElideRight, largeur)

    def _ligne(self, avant_poste, mien: bool, zebre: bool,
               mesures: Mesures) -> QWidget:
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
        bloc.setFixedWidth(mesures.bloc)
        ligne = QHBoxLayout(bloc)
        ligne.setContentsMargins(0, 0, 0, 0)
        ligne.setSpacing(ESPACEMENT)

        # L'embleme de la guilde, charge en tache de fond et mis en cache.
        embleme = QLabel()
        cote = self._fenetre.reglages.icone(PART_EMBLEME)
        embleme.setFixedWidth(cote)
        self._fenetre.icones.demander_embleme(
            avant_poste.icon, self._rappel_embleme(embleme, cote))
        ligne.addWidget(embleme)

        # **`#compact` pour les trois, la couleur par-dessus.** GTK cumule
        # ses classes : le nom porte `.compact` pour le corps et `.fini` pour
        # le vert, le niveau `.compact` et `.dim-label`. Qt n'a qu'un
        # identifiant par widget -- prendre `#fini` ou `#discret` faisait
        # perdre le corps reduit, et une ligne qui nous appartient s'ecrivait
        # plus gros que ses voisines.
        nom = QLabel()
        nom.setObjectName("compact")
        if mien:
            nom.setProperty("fini", True)
        nom.setFixedWidth(mesures.nom)
        nom.setText(self._abreger(
            nom, self._fenetre.noms.name(avant_poste.name_key), mesures.nom))
        ligne.addWidget(nom)

        niveau = QLabel(str(avant_poste.level) if avant_poste.level else "—")
        niveau.setObjectName("compact")
        niveau.setProperty("discret", True)
        niveau.setFixedWidth(mesures.niveau)
        niveau.setAlignment(Qt.AlignmentFlag.AlignRight
                            | Qt.AlignmentFlag.AlignVCenter)
        ligne.addWidget(niveau)

        guilde = QLabel()
        guilde.setObjectName("compact")
        if mien:
            guilde.setProperty("fini", True)
        guilde.setText(self._abreger(guilde, avant_poste.guild,
                                     mesures.guilde))
        # Le dernier prend ce qui reste : les trois largeurs font le bloc, il
        # recoit donc exactement la sienne.
        ligne.addWidget(guilde, 1)

        exterieur.addWidget(bloc)
        exterieur.addStretch(1)
        return rangee

    def resizeEvent(self, evenement) -> None:       # noqa: N802
        """Retaille les colonnes quand la page change franchement de largeur.

        Les trois colonnes sont calculees pour la place offerte au moment du
        remplissage. GTK n'a pas ce souci -- ses `SizeGroup` et son
        `ellipsize` suivent le widget toute sa vie ; en Qt les largeurs sont
        posees une fois pour toutes, il faut donc refaire la carte.

        Pas a chaque pixel : l'ascenseur vertical qui parait ou disparait en
        vaut dix a lui seul, et la carte refaite peut justement le faire
        paraitre -- deux largeurs qui s'appelleraient l'une l'autre sans fin.
        """
        super().resizeEvent(evenement)
        if not self._carte or self._dd_vue.currentIndex() == 1:
            return
        if abs(self.width() - self._largeur_remplie) < SEUIL_REDIMENSION:
            return
        self._largeur_remplie = self.width()
        # Apres l'evenement, et non pendant : on ne refait pas un affichage
        # que Qt est en train de poser.
        QTimer.singleShot(0, self._rafraichir)

    @staticmethod
    def _rappel_embleme(cible: QLabel, cote: int):
        def arrivee(chemin):
            if not chemin:
                return
            image = QPixmap(chemin)
            if image.isNull():
                return
            try:
                cible.setPixmap(image.scaledToWidth(
                    cote, Qt.TransformationMode.SmoothTransformation))
            except RuntimeError:
                # La carte a ete refaite pendant que l'embleme voyageait --
                # un changement d'entite, ou la fenetre redimensionnee. Le
                # libelle vise n'existe plus du cote C++, et Python l'apprend
                # par cette exception. Rien a faire : la ligne qui l'a
                # remplace a redemande la meme image, qui est en cache.
                pass
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
