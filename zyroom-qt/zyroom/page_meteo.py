"""La météo d'Atys en courbe, et les matières qu'elle fait sortir.

Deux sources : l'API officielle pour le temps — calculé par le jeu, donc connu
quarante cycles à l'avance — et un relevé de Ryzom Armory figé dans
`armory.py`, qui ne changera qu'avec le jeu.

**Le temps d'Atys avance tout seul.** On ne redemande rien : l'affichage se
recale toutes les dix secondes, soit un pas de trois heures et vingt d'Atys —
le trait du présent glisse au lieu de sauter. On ne va rechercher un relevé que
lorsque la prévision touche à sa fin.
"""
from __future__ import annotations

import html
from datetime import datetime, timedelta

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)

from . import gisements, meteo, page_gisements, ryzom_api
from . import theme
from .i18n import _

#: Ce que la courbe montre, en heures d'Atys, et ou s'y tient le present.
#:
#: Vingt-quatre heures d'Atys valent soixante-douze minutes reelles : de quoi
#: voir une heure d'avance et un bon quart d'heure de passe. Le trait du
#: present se tient a un sixieme de la largeur -- c'est ce qui vient qui
#: compte, le passe ne sert qu'a comprendre d'ou l'on sort.
FENETRE_HEURES = 24.0
ANCRE = 0.15

#: La duree de la bascule d'un palier au suivant, en heures d'Atys. C'est le
#: code du jeu qui la donne (`CPredictWeather::predictWeather`, ryzomcore) :
#: la derniere heure de chaque cycle, le taux glisse en ligne droite vers celui
#: du cycle suivant et l'atteint pile au changement de cycle. Centree sur ce
#: changement, la bascule avait une minute et demie de retard sur le jeu.
TRANSITION_HEURES = 1.0

#: Les reperes d'heure reelle sous l'axe.
#:
#: `MINUTES_ENTRE_REPERES` est le pas des heures ecrites ; les tirets, eux,
#: tombent cinq fois plus souvent. Le quart d'heure suffit a ecrire une heure,
#: mais pas a lire une prevision : entre deux reperes passent cinq heures
#: d'Atys, et viser un creux demandait d'interpoler a l'oeil sur soixante
#: pixels. Voir `window.py` du cote GTK, qui porte la meme decision.
MINUTES_ENTRE_REPERES = 15
MINUTES_ENTRE_TIRETS = 5
PAS_DE_TEMPS = 48

#: Longueur des tirets sous l'axe, en pixels : celui qui porte une heure, puis
#: le muet. Deux et trois ne se voyaient pas -- un tiret muet n'a que sa propre
#: encre pour exister, la ou un repere d'heure se trouve en lisant l'heure.
LONGUEUR_TIRET_ECRIT = 6
LONGUEUR_TIRET_MUET = 4

#: Leur opacite, de zero a 255 -- les memes valeurs que GTK, qui les ecrit de
#: zero a un : 0,62 et 0,42. Le muet reste en retrait, c'est ce qui laisse
#: lire le quart d'heure sans compter les tirets. L'heure ecrite, elle, ne
#: bouge pas.
OPACITE_TIRET_ECRIT = 158
OPACITE_TIRET_MUET = 107

#: Hauteur de la ligne des heures au-dessus du bas du graphique, en pixels.
#:
#: Quatre, et non six : l'axe se tient a vingt pixels du bas et le tiret qui
#: porte une heure en descend six, si bien qu'il finissait a un pixel du haut
#: des chiffres et venait mordre dessus. Voir `window.py` du cote GTK.
PIED_DES_HEURES = 4

#: Taille des symboles de familles de matieres, en pixels.
#:
#: Vingt-six : sur un ecran de bureau, a cote d'un nom de famille et d'une
#: ligne de matieres, vingt faisaient une vignette qu'on devinait plus qu'on
#: ne la reconnaissait.
PART_SYMBOLE = 0.54

#: Colonnes du bloc "ce qui sort" -- une par zone des Primes, pour les avoir
#: toutes les quatre sous les yeux a la fois.
COLONNES_POP = 4


class CourbeMeteo(QWidget):
    """L'humidité dans le temps, **en paliers reliés par des obliques**.

    Une valeur vaut pour tout un cycle — trois heures d'Atys, neuf minutes
    réelles : c'est le palier, et c'est lui qui décide de la condition de
    gisement. Relier simplement les points par des obliques dessinerait des
    crêtes qui n'existent pas, et déplacerait les moments intéressants : la
    fenêtre excellente n'est pas un sommet qu'on rate, c'est un palier qui
    dure.

    **C'est le graphique qui défile, pas le trait.** Le présent se tient près
    du bord gauche et la courbe glisse dessous, comme un sismographe : on garde
    ainsi toujours la même avance sous les yeux, au lieu de voir le trait
    dériver jusqu'à sortir de la vue.
    """

    def __init__(self, releve_fn) -> None:
        super().__init__()
        self._releve = releve_fn
        self.setMinimumHeight(190)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def paintEvent(self, _event) -> None:            # noqa: N802 -- nom Qt
        releve = self._releve()
        if releve is None:
            return
        cycles = releve.cycles_des_primes()
        if len(cycles) < 2:
            return

        largeur, hauteur = float(self.width()), float(self.height())
        marge_g, marge_b = 34.0, 20.0
        large = largeur - marge_g
        haut = hauteur - marge_b
        if large <= 0 or haut <= 0:
            return

        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        police = QFont()
        # Au zoom courant : le texte peint ne passe pas par la feuille.
        police.setPointSizeF(8 * theme.zoom_courant())
        peintre.setFont(police)

        # Tout se repere en heures d'Atys, et non en indices de cycle : c'est
        # ce qui permet a la fenetre de glisser continument sous un trait fixe.
        gauche = releve.heure_atys - ANCRE * FENETRE_HEURES

        def x(heure: float) -> float:
            return marge_g + large * (heure - gauche) / FENETRE_HEURES

        def y(valeur: float) -> float:
            return haut * (1.0 - min(1.0, max(0.0, valeur)))

        peintre.save()
        peintre.setClipRect(QRectF(marge_g, 0, large, haut))

        # Les nuits, comptees par heure et non par cycle : un cycle de trois
        # heures enjambe volontiers le lever du jour.
        peintre.setPen(Qt.PenStyle.NoPen)
        peintre.setBrush(QColor(255, 255, 255, 15))
        premiere = int(gauche) - 1
        for heure in range(premiere, int(gauche + FENETRE_HEURES) + 2):
            if meteo.est_la_nuit(heure % 24):
                peintre.drawRect(QRectF(x(heure), 0,
                                        large / FENETRE_HEURES, haut))

        # La courbe et son aire. Un cycle couvre trois heures : le palier
        # tient les deux premieres, et la derniere rejoint le palier suivant
        # en oblique -- comme le fait le jeu.
        def paliers():
            for m in cycles:
                debut = m.cycle * meteo.HEURES_PAR_CYCLE
                yield (x(debut),
                       x(debut + meteo.HEURES_PAR_CYCLE - TRANSITION_HEURES),
                       y(m.value))

        from PySide6.QtGui import QPainterPath
        aire = QPainterPath()
        aire.moveTo(x(cycles[0].cycle * meteo.HEURES_PAR_CYCLE), haut)
        for gx, dx, py in paliers():
            aire.lineTo(gx, py)
            aire.lineTo(dx, py)
        aire.lineTo(x((cycles[-1].cycle + 1) * meteo.HEURES_PAR_CYCLE), haut)
        aire.closeSubpath()
        peintre.fillPath(aire, QColor(64, 122, 105, 90))

        trait = QPainterPath()
        premier = True
        for gx, dx, py in paliers():
            if premier:
                trait.moveTo(gx, py)
                premier = False
            else:
                trait.lineTo(gx, py)
            trait.lineTo(dx, py)
        peintre.setBrush(Qt.BrushStyle.NoBrush)
        peintre.setPen(QPen(QColor(89, 173, 148), 2.0))
        peintre.drawPath(trait)
        peintre.restore()

        # Deux graduations, plus discretes que les seuils : elles ne veulent
        # rien dire pour le jeu, elles servent seulement a situer un taux a
        # l'oeil entre deux seuils ecartes de trente points. Traits pleins et
        # non pointilles, pour qu'on ne les confonde pas avec les seuils.
        # Trente-trois et soixante-six, et non trente et soixante-dix : ce
        # sont les graduations du graphe de Ballistic Mystix, celui qu'on
        # ouvre a cote pour verifier, et les six bandes des classeurs de la
        # guilde. Deux echelles qui ne tombent pas aux memes hauteurs ne se
        # comparent pas d'un coup d'oeil.
        for graduation, etiquette in ((0.334, "33,4"), (0.666, "66,6")):
            yy = y(graduation)
            peintre.setPen(QPen(QColor(255, 255, 255, 46), 1.0))
            peintre.drawLine(QPointF(marge_g, yy), QPointF(largeur, yy))
            peintre.setPen(QColor(255, 255, 255, 90))
            peintre.drawText(QPointF(2, yy - 3), etiquette)

        # Les seuils du jeu, par-dessus la courbe, et leur etiquette en marge.
        pointille = QPen(QColor(230, 102, 102, 140), 1.0)
        pointille.setStyle(Qt.PenStyle.DashLine)
        for seuil, etiquette in zip(meteo.SEUILS, ("16,7", "50", "83,4")):
            yy = y(seuil)
            peintre.setPen(pointille)
            peintre.drawLine(QPointF(marge_g, yy), QPointF(largeur, yy))
            peintre.setPen(QColor(255, 255, 255, 140))
            peintre.drawText(QPointF(2, yy - 3), etiquette)

        # Le present, immobile pres du bord gauche.
        px = x(releve.heure_atys)
        peintre.setPen(QPen(QColor(232, 193, 90), 2.0))
        peintre.drawLine(QPointF(px, 0), QPointF(px, haut))

        peintre.setPen(QPen(QColor(255, 255, 255, 90), 1.0))
        peintre.drawLine(QPointF(marge_g, haut), QPointF(largeur, haut))

        # L'heure reelle, tous les quarts d'heure -- et un tiret toutes les
        # cinq minutes entre elles. Une heure d'Atys valant trois minutes, la
        # fenetre ne couvre que soixante-douze minutes reelles : a l'heure
        # ronde, il n'y aurait qu'un repere, parfois zero.
        maintenant = datetime.now()
        repere = maintenant.replace(minute=0, second=0,
                                    microsecond=0) - timedelta(hours=1)
        for _pas in range(PAS_DE_TEMPS):
            repere += timedelta(minutes=MINUTES_ENTRE_TIRETS)
            minutes = (repere - maintenant).total_seconds() / 60.0
            atys = releve.heure_atys + minutes / meteo.MINUTES_PAR_HEURE_ATYS
            if not gauche <= atys <= gauche + FENETRE_HEURES:
                continue
            # Deux longueurs de tiret, une seule ecriture : voir `window.py`
            # du cote GTK. Le tiret dit ou tombe l'instant, l'heure ecrite dit
            # lequel c'est -- quinze nombres sur une largeur qui en tient cinq
            # ne se liraient plus.
            ecrite = repere.minute % MINUTES_ENTRE_REPERES == 0
            peintre.setPen(QPen(QColor(255, 255, 255,
                                       OPACITE_TIRET_ECRIT if ecrite
                                       else OPACITE_TIRET_MUET), 1.0))
            peintre.drawLine(
                QPointF(x(atys), haut),
                QPointF(x(atys), haut + (LONGUEUR_TIRET_ECRIT if ecrite
                                         else LONGUEUR_TIRET_MUET)))
            if not ecrite:
                continue
            peintre.setPen(QColor(255, 255, 255, 140))
            texte = (repere.strftime("%Hh") if repere.minute == 0
                     else repere.strftime("%Hh%M"))
            peintre.drawText(QPointF(min(largeur - 30, max(0.0, x(atys) - 14)),
                                     hauteur - PIED_DES_HEURES), texte)


class PageMeteo(QWidget):
    def __init__(self, fenetre) -> None:
        super().__init__()
        self._fenetre = fenetre
        self._releve = None        #: ce que l'API a rendu, tel quel
        self._affiche = None       #: le meme, recale sur l'instant present
        self._charge = False
        self._en_cours = False

        colonne = QVBoxLayout(self)
        colonne.setContentsMargins(0, 0, 0, 0)
        colonne.setSpacing(4)

        barre = QWidget()
        ligne = QHBoxLayout(barre)
        # Douze en bas : avec les quatre d'ecart de la colonne, cela
        # fait les seize pixels qui separent la barre de la courbe en
        # GTK -- huit sous la barre, huit au-dessus de la courbe, que
        # `_pad` pose sur l'une et sur l'autre.
        ligne.setContentsMargins(8, 8, 8, 12)
        ligne.setSpacing(8)
        self._entete = QLabel()
        self._entete.setWordWrap(True)
        ligne.addWidget(self._entete, 1)
        self._btn_actualiser = QPushButton(_("Actualiser"))
        self._btn_actualiser.clicked.connect(lambda: self.charger(force=True))
        ligne.addWidget(self._btn_actualiser)
        colonne.addWidget(barre)

        self._courbe = CourbeMeteo(lambda: self._affiche or self._releve)
        self._courbe.setContentsMargins(8, 0, 8, 0)
        colonne.addWidget(self._courbe)

        # Deux colonnes, et **un seul defilement pour tout**. Chacune a d'abord
        # eu le sien ; a l'usage, deux barres sont pires : on ne sait plus
        # laquelle on tient, et comparer deux tableaux qui glissent separement
        # demande de les recaler a la main.
        contenu = QWidget()
        dedans = QVBoxLayout(contenu)
        dedans.setContentsMargins(8, 8, 8, 8)
        dedans.setSpacing(2)

        # Ce qui sort maintenant, en tete et sur toute la largeur : c'est la
        # seule chose de cet ecran qui depende de l'instant.
        self._pop_titre = QLabel()
        self._pop_titre.setObjectName("peuple")
        dedans.addWidget(self._pop_titre)
        pop = QWidget()
        rangee = QHBoxLayout(pop)
        rangee.setContentsMargins(0, 0, 0, 0)
        rangee.setSpacing(12)
        self._pop_colonnes = []
        for _rang in range(COLONNES_POP):
            porteur = QWidget()
            pile = QVBoxLayout(porteur)
            pile.setContentsMargins(0, 0, 0, 0)
            pile.setSpacing(2)
            self._pop_colonnes.append(pile)
            rangee.addWidget(porteur, 1)
        dedans.addWidget(pop)

        # Le tableau des excellentes de la saison, jour et nuit cote a cote,
        # a ete retire. Il disait la saison entiere quand "ce qui sort" dit
        # l'instant, et il tenait le jour et la nuit du releve d'Armory alors
        # que le releve de la guilde, lui, range les excellentes par saison et
        # par temps -- comme les supremes. Les deux listes se contredisaient
        # sur l'ecorce et la resine.

        self._note = QLabel(
            _("Les Primes partagent une seule météo, mais pas les mêmes pops : "
              "chaque zone dit la sienne. Un spot suprême vidé met quinze "
              "jours à se recharger — les bonnes conditions ne suffisent pas. "
              "Le suprême a été relevé en jeu, case par case ; une partie de "
              "l'excellente est rapportée et reste à confirmer. "
              "Positions de ballisticmystix.net."))
        self._note.setObjectName("discret")
        self._note.setWordWrap(True)
        self._note.setContentsMargins(0, 8, 0, 0)
        dedans.addWidget(self._note)
        dedans.addStretch(1)

        defilant = QScrollArea()
        defilant.setWidget(contenu)
        defilant.setWidgetResizable(True)
        defilant.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        colonne.addWidget(defilant, 1)

        self._minuteur = QTimer(self)
        self._minuteur.timeout.connect(self._battement)

    # -------------------------------------------------------- Chargement
    def charger(self, force: bool = False) -> None:
        if self._charge and not force:
            return
        self._charge = True
        self._en_cours = True
        self._btn_actualiser.setEnabled(False)
        self._entete.setText(_("Lecture de la météo…"))

        def travail():
            continents = sorted(set(meteo.CONTINENT_DE_ZONE.values()))
            # Quelques cycles deja ecoules en plus : sans eux la courbe
            # commencerait a l'instant present, et le trait du "maintenant"
            # se collerait au bord gauche.
            brut = ryzom_api.fetch_weather_json(continents, cycles=20, passes=6)
            releve = meteo.parse_weather(brut)
            # La saison vient d'un autre appel : le flux meteo ne la porte pas,
            # et c'est elle qui dit quelle page du releve regarder.
            try:
                saison = ryzom_api.parse_time(
                    ryzom_api.fetch_time_xml())["season_index"]
            except Exception:                           # noqa: BLE001
                saison = -1
            return meteo.MeteoAtys(releve.cycle_courant, releve.heure_atys,
                                   saison, releve.continents, releve.pris_a)

        def apres(resultat, erreur):
            self._en_cours = False
            self._btn_actualiser.setEnabled(True)
            if erreur:
                self._entete.setText(_("Météo indisponible : %s") % erreur)
                return
            self._releve = resultat
            self._affiche = resultat
            self.rafraichir()
            # Le temps d'Atys avance tout seul : on ne redemande rien, on
            # recale l'affichage. Toutes les dix secondes, soit un pas de trois
            # heures et vingt d'Atys -- le trait glisse au lieu de sauter.
            if not self._minuteur.isActive():
                self._minuteur.start(10_000)

        self._fenetre.passerelle.lancer(travail, apres)

    def hideEvent(self, event) -> None:          # noqa: N802 -- nom impose
        """Arrête le battement quand on quitte l'écran.

        Il refait la courbe et les blocs de matières toutes les dix secondes :
        des dizaines de widgets détruits et recréés, six fois par minute,
        indéfiniment. Page fermée, personne ne les regarde — et au bout de
        quelques heures l'application n'avançait plus.
        """
        self._minuteur.stop()
        super().hideEvent(event)

    def showEvent(self, event) -> None:          # noqa: N802 -- nom impose
        """Reprend le battement en revenant, si l'on a déjà un relevé."""
        if self._releve is not None and not self._minuteur.isActive():
            self._minuteur.start(10_000)
        super().showEvent(event)

    def _battement(self) -> None:
        """Fait avancer l'heure d'Atys, sans rien demander à personne.

        Les cycles reçus couvrent plusieurs heures réelles : tant que le trait
        du « maintenant » reste dans la série, il n'y a aucune raison de
        redemander quoi que ce soit. Quand il approche du bout, on redemande —
        **une fois**, et sans cesser d'avancer pendant ce temps.
        """
        if self._releve is None:
            self._minuteur.stop()
            return
        avance = self._releve.a_present()
        cycles = avance.cycles_des_primes()
        if cycles and not self._en_cours and avance.cycle_courant >= cycles[-1].cycle - 2:
            self.charger(force=True)
        self._affiche = avance
        self.rafraichir()
        # Les cartes de gisements laissees ouvertes suivent le meme battement :
        # leurs points verts et gris dependent du cycle en cours.
        page_gisements.rafraichir_ouvertes(self)

    # ---------------------------------------------------------- Affichage
    @staticmethod
    def _vider(pile: QVBoxLayout) -> None:
        while pile.count():
            element = pile.takeAt(0)
            if element.widget():
                element.widget().deleteLater()

    def rafraichir(self) -> None:
        releve = self._affiche or self._releve
        if releve is None:
            return
        self._maj_entete(releve)
        self._courbe.update()

        for pile in self._pop_colonnes:
            self._vider(pile)

        # Ce qui sort maintenant, une colonne par zone : l'humidite decide de
        # la condition, la condition decide de la qualite, et la qualite decide
        # de ce qu'on trouve. Chaque zone dit tout ce qu'elle sort, supreme
        # puis XL, chaque bloc sous le nom de sa qualite : n'afficher que la
        # meilleure masquerait quinze XL derriere une seule supreme aux
        # Sources Interdites, en automne par temps mauvais.
        actuelle = releve.maintenant()
        if actuelle is None:
            self._pop_titre.setText("")
        else:
            # Le titre nomme la liste, et rien d'autre. Il a porte tour a tour
            # la qualite du moment, puis un compte a rebours vers la fenetre
            # execrable : les deux servaient d'en-tete aux quatre colonnes et
            # faisaient lire la liste comme une prevision.
            self._pop_titre.setText(_("MP qui pop maintenant"))
            for rang, zone in enumerate(meteo.ZONES):
                blocs = meteo.sorties_de(releve.saison, zone,
                                         actuelle.condition)
                pile = self._pop_colonnes[rang % COLONNES_POP]
                # `AlignTop`, sans quoi Qt etire le bloc pour remplir sa
                # colonne et centre son contenu : les quatre zones n'ayant pas
                # le meme nombre de matieres, leurs titres ne s'alignaient plus
                # d'une colonne a l'autre. GTK empile par le haut d'office.
                pile.addWidget(self._bloc_matieres(
                    zone, blocs, rang // COLONNES_POP % 2 == 0),
                    0, Qt.AlignmentFlag.AlignTop)

    def _maj_entete(self, releve) -> None:
        maintenant = releve.maintenant()
        if maintenant is None:
            return
        suite = [c for c in releve.cycles_des_primes()
                 if c.cycle > releve.cycle_courant]
        prochain = next((c for c in suite
                         if c.condition != maintenant.condition), None)

        # Chaque morceau est echappe pour lui-meme, et le gras pose ensuite :
        # echapper la phrase entiere puis remettre les balises a la main
        # marcherait, mais cederait au premier nom contenant un "&".
        def gras(texte: str) -> str:
            return f"<b>{html.escape(texte)}</b>"

        # La ligne se lisait "Beau · 0 % -> Excellente   Mauvaise dans 5 min".
        # Trois nombres, une fleche, et deux conditions cote a cote dont l'une
        # etait la suivante : il fallait connaitre le code pour la decoder.
        # Elle se lit maintenant comme une phrase :
        #
        #   humidite mauvaise 61 %, sort supreme et XL pendant 4 min
        #     - beau, ete, 22 h sur Atys, nuit
        #
        # Les conditions en minuscules : "mauvaise" qualifie l'humidite qui
        # precede, et la capitale en faisait un nom propre qu'on lisait comme
        # une qualite de matiere.
        #
        # **"excellente dans 1 h 12" a ete retiree.** Elle comptait vers le
        # prochain cycle par temps sec -- la condition "best" du jeu. Mais
        # "excellente" nomme aussi une qualite de matiere, et la ligne venait
        # d'ecrire "sort supreme et XL" : le meme mot y designait une bande
        # d'humidite et ce qu'on fore. La courbe, juste dessous, montre de
        # toute facon quand le taux redescend.
        morceaux = [
            html.escape(_("humidité ")),
            gras(f"{meteo.texte_condition(maintenant.condition).lower()} "
                 f"{int(maintenant.value * 100)} %"),
        ]
        qualites = self._qualites_du_moment(releve, maintenant)
        if qualites:
            morceaux.append(html.escape(_(", sort ")))
            morceaux.append(gras(meteo.enumere_qualites(qualites)))
        if prochain is not None:
            # Le temps qui reste, et non le nom de la condition d'apres :
            # "pendant 4 min" repond a "est-ce que j'ai le temps ?".
            morceaux.append(gras(
                _(" pendant %s")
                % meteo.duree(releve.minutes_avant(prochain.cycle))))
        morceaux.append(html.escape(
            f"   —   {meteo.texte_meteo(maintenant.text).lower()}, "
            f"{meteo.nom_saison(releve.saison).lower()}, "
            f"{releve.heure_du_jour} h sur Atys, "
            f"{'nuit' if releve.nuit else 'jour'}"))
        self._entete.setText("".join(morceaux))

    @staticmethod
    def _qualites_du_moment(releve, actuelle):
        """Toutes les qualites que sortent les Primes a cet instant.

        Elles se lisent dans le releve de la guilde, zone par zone, et non
        dans une regle ecrite a la main. La regle disait "supreme seulement
        par temps execrable, et sinon rien" : c'etait honnete tant que la XL
        etait devinee a partir des fourchettes d'humidite -- une fourchette
        dit **ou** l'on trouve une matiere, pas en quelle qualite elle sort.

        **Toutes, et non la meilleure.** Par temps mauvais aux Sources
        Interdites, il sort une supreme et quinze XL : n'annoncer que la
        supreme taisait les quinze, qui sont justement ce qu'on va forer
        faute de mieux.
        """
        connues = {q for zone in meteo.ZONES
                   for q, _g in meteo.sorties_de(releve.saison, zone,
                                                 actuelle.condition)}
        return [q for q in meteo.QUALITES if q in connues]

    @staticmethod
    def _matieres_html(qualite: str, famille: str, matieres: list) -> str:
        """La liste des matières, celles qu'on sait situer devenant des liens.

        Un lien plutôt qu'un bouton : la liste garde son allure de phrase et
        continue de se replier toute seule quand la colonne rétrécit. Une
        matière sans carte reste du texte ordinaire — rien n'invite à cliquer
        sur ce qui ne répondrait pas.
        """
        morceaux = []
        # Les gisements sont releves par qualite, et sous un autre nom que
        # celui de l'ecran. Le choix, lui, n'est releve nulle part : ses
        # matieres restent du texte.
        nom = meteo.QUALITE_GISEMENT.get(qualite, "")
        for matiere in matieres:
            texte = html.escape(matiere)
            if meteo.positions_des_primes(qualite, famille, matiere):
                cible = html.escape(f"{nom}|{famille}|{matiere}")
                morceaux.append(f'<a href="{cible}">{texte}</a>')
            else:
                morceaux.append(texte)
        return ", ".join(morceaux)

    def _on_gisement(self, adresse: str) -> None:
        page_gisements.montrer(self, *adresse.split("|", 2))

    def _bloc_matieres(self, titre: str, blocs: list, zebre: bool) -> QWidget:
        """Une zone : son nom, puis un sous-bloc par qualite qu'elle sort.

        `blocs` est ce que rend `meteo.sorties_de` -- la meilleure qualite
        d'abord. Chacune porte son nom et son compte, sans quoi une XL
        affichee sous une supreme se lirait comme une supreme, et une seule
        supreme s'annoncerait comme les vingt et une de l'execrable.
        """
        boite = QWidget()
        # Sans cet attribut, Qt ne peint pas le fond que la feuille
        # de style donne a un QWidget nu.
        boite.setAttribute(
            Qt.WidgetAttribute.WA_StyledBackground, True)
        if zebre:
            boite.setProperty("zebre", True)
        colonne = QVBoxLayout(boite)
        colonne.setContentsMargins(8, 8, 8, 8)
        colonne.setSpacing(1)

        entete = QLabel(titre)
        entete.setObjectName("titre")
        colonne.addWidget(entete)

        if not blocs:
            vide = QLabel(_("Pas encore relevé"))
            vide.setObjectName("discret")
            colonne.addWidget(vide)
        for qualite, groupes in blocs:
            # L'or de l'application, et non le gris attenue : c'est le mot
            # qu'on cherche des yeux en parcourant les quatre colonnes, et il
            # etait plus pale que les matieres qu'il annonce.
            combien = sum(len(m) for m in groupes.values())
            rappel = QLabel(f"{meteo.mot_qualite(qualite)} ({combien})")
            rappel.setObjectName("peuple")
            rappel.setContentsMargins(0, 4, 0, 0)
            colonne.addWidget(rappel)
            colonne.addWidget(self._grille_matieres(qualite, groupes))
        return boite

    def _grille_matieres(self, qualite: str, groupes: dict) -> QWidget:
        porteur = QWidget()
        grille = QGridLayout(porteur)
        grille.setContentsMargins(0, 0, 0, 0)
        grille.setHorizontalSpacing(12)
        grille.setVerticalSpacing(1)
        grille.setColumnStretch(1, 1)

        for rang, (groupe, matieres) in enumerate(sorted(groupes.items())):
            # Le nom de la famille, et sous lui son symbole du jeu : une
            # coquille pour la carapace, une goutte pour la seve. Ce sont ceux
            # qu'on a sous les yeux en forant, et l'oeil les reconnait plus
            # vite qu'il ne lit "Carapace".
            cellule = QWidget()
            # Un minimum, et non une largeur fixe -- comme `set_size_request`
            # cote GTK. Fixee, la colonne se calculait sur la police du widget
            # a sa creation, avant que le theme ne l'agrandisse : « Carapace »
            # et « Ambres » s'y faisaient couper par la liste des matieres.
            cellule.setMinimumWidth(theme.largeur(cellule, 4.7))
            pile = QVBoxLayout(cellule)
            pile.setContentsMargins(0, 0, 0, 0)
            pile.setSpacing(0)
            nom_groupe = QLabel(groupe)
            nom_groupe.setObjectName("discret")
            pile.addWidget(nom_groupe)
            chemin = meteo.symbole(groupe)
            if chemin:
                image = QLabel()
                image.setPixmap(QPixmap(chemin).scaledToHeight(
                    self._fenetre.reglages.icone(PART_SYMBOLE),
                    Qt.TransformationMode.SmoothTransformation))
                image.setAlignment(Qt.AlignmentFlag.AlignLeft)
                pile.addWidget(image)
            pile.addStretch(1)
            grille.addWidget(cellule, rang, 0, Qt.AlignmentFlag.AlignTop)

            liste = QLabel(self._matieres_html(qualite, groupe, matieres))
            liste.setWordWrap(True)
            # Le lien porte sa cible dans son adresse ; `linkActivated` la
            # rend telle quelle, et rien ne part vers un navigateur.
            liste.linkActivated.connect(self._on_gisement)
            grille.addWidget(liste, rang, 1, Qt.AlignmentFlag.AlignTop)

        return porteur
