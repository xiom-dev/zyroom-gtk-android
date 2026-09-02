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

from . import armory, gisements, meteo, page_gisements, ryzom_api
from .i18n import _

#: Ce que la courbe montre, en heures d'Atys, et ou s'y tient le present.
#:
#: Vingt-quatre heures d'Atys valent soixante-douze minutes reelles : de quoi
#: voir une heure d'avance et un bon quart d'heure de passe. Le trait du
#: present se tient a un sixieme de la largeur -- c'est ce qui vient qui
#: compte, le passe ne sert qu'a comprendre d'ou l'on sort.
FENETRE_HEURES = 24.0
ANCRE = 0.15

#: La duree de la bascule d'un palier au suivant, en heures d'Atys. Le taux
#: monte et descend graduellement ; un trait vertical laisserait croire le
#: contraire.
TRANSITION_HEURES = 1.0

#: Les reperes d'heure reelle sous l'axe.
MINUTES_ENTRE_REPERES = 15
PAS_DE_TEMPS = 16

#: Taille des symboles de familles de matieres, en pixels.
#:
#: Vingt-six : sur un ecran de bureau, a cote d'un nom de famille et d'une
#: ligne de matieres, vingt faisaient une vignette qu'on devinait plus qu'on
#: ne la reconnaissait.
TAILLE_SYMBOLE = 26

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
        police.setPointSize(8)
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

        # La courbe et son aire. Un cycle couvre trois heures ; le palier
        # occupe le milieu, et la demi-heure de part et d'autre sert a
        # rejoindre le palier voisin en oblique.
        def paliers():
            demi = TRANSITION_HEURES / 2
            for m in cycles:
                debut = m.cycle * meteo.HEURES_PAR_CYCLE
                yield (x(debut + demi),
                       x(debut + meteo.HEURES_PAR_CYCLE - demi),
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
        for graduation, etiquette in ((0.30, "30"), (0.70, "70")):
            yy = y(graduation)
            peintre.setPen(QPen(QColor(255, 255, 255, 46), 1.0))
            peintre.drawLine(QPointF(marge_g, yy), QPointF(largeur, yy))
            peintre.setPen(QColor(255, 255, 255, 90))
            peintre.drawText(QPointF(2, yy - 3), etiquette)

        # Les seuils du jeu, par-dessus la courbe, et leur etiquette en marge.
        pointille = QPen(QColor(230, 102, 102, 140), 1.0)
        pointille.setStyle(Qt.PenStyle.DashLine)
        for seuil, etiquette in zip(meteo.SEUILS, ("16", "50", "83")):
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

        # L'heure reelle, tous les quarts d'heure. Une heure d'Atys valant
        # trois minutes, la fenetre ne couvre que soixante-douze minutes
        # reelles : a l'heure ronde, il n'y aurait qu'un repere, parfois zero.
        maintenant = datetime.now()
        repere = maintenant.replace(minute=0, second=0,
                                    microsecond=0) - timedelta(hours=1)
        for _pas in range(PAS_DE_TEMPS):
            repere += timedelta(minutes=MINUTES_ENTRE_REPERES)
            minutes = (repere - maintenant).total_seconds() / 60.0
            atys = releve.heure_atys + minutes / meteo.MINUTES_PAR_HEURE_ATYS
            if not gauche <= atys <= gauche + FENETRE_HEURES:
                continue
            # Un trait court sous l'axe, puis l'heure : sans lui, on lit bien
            # l'heure mais on ne sait pas au pixel pres ou elle tombe.
            peintre.setPen(QPen(QColor(255, 255, 255, 90), 1.0))
            peintre.drawLine(QPointF(x(atys), haut), QPointF(x(atys), haut + 3))
            peintre.setPen(QColor(255, 255, 255, 140))
            texte = (repere.strftime("%Hh") if repere.minute == 0
                     else repere.strftime("%Hh%M"))
            peintre.drawText(QPointF(min(largeur - 30, max(0.0, x(atys) - 14)),
                                     hauteur - 6), texte)


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
        ligne.setContentsMargins(8, 8, 8, 0)
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

        self._excellentes = QVBoxLayout()
        self._excellentes.setContentsMargins(0, 0, 0, 0)
        porteur_exc = QWidget()
        porteur_exc.setLayout(self._excellentes)
        dedans.addWidget(porteur_exc)

        # Jour a gauche, nuit a droite. L'un sous l'autre, il fallait derouler
        # la liste de jour pour atteindre celle de nuit -- alors que le seul
        # geste utile est de les comparer.
        moments = QWidget()
        duo = QHBoxLayout(moments)
        duo.setContentsMargins(0, 0, 0, 0)
        duo.setSpacing(12)
        self._jour = QVBoxLayout()
        self._nuit = QVBoxLayout()
        for pile in (self._jour, self._nuit):
            porteur = QWidget()
            porteur.setLayout(pile)
            pile.setContentsMargins(0, 0, 0, 0)
            pile.setSpacing(2)
            duo.addWidget(porteur, 1)
        dedans.addWidget(moments)

        self._note = QLabel(
            _("Les Primes partagent une seule météo : celle-ci vaut pour les "
              "quatre zones."))
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

        for pile in (self._excellentes, self._jour, self._nuit,
                     *self._pop_colonnes):
            self._vider(pile)

        cle = releve.saison_cle
        saison = meteo.nom_saison(releve.saison)

        # Ce qui sort maintenant, une colonne par zone : l'humidite decide de
        # la condition de gisement, la condition decide de ce qu'on trouve, et
        # le bloc change tout seul a chaque bascule de cycle.
        actuelle = releve.maintenant()
        if actuelle is None:
            self._pop_titre.setText("")
        else:
            self._pop_titre.setText(
                _("Suprêmes — ce qui sort : %(condition)s, %(taux)d %%")
                % {"condition": meteo.texte_condition(actuelle.condition),
                   "taux": round(actuelle.value * 100)})
            remplies = [(zone, meteo.pop_de(releve.saison, zone,
                                            actuelle.condition))
                        for zone in meteo.ZONES]
            remplies = [(z, g) for z, g in remplies if g]
            for rang, (zone, groupes) in enumerate(remplies):
                pile = self._pop_colonnes[rang % COLONNES_POP]
                pile.addWidget(self._bloc_matieres(
                    zone, groupes, rang // COLONNES_POP % 2 == 0,
                    qualite="supreme"))

        self._excellentes.addWidget(self._entete_colonne(_("Cette saison")))
        self._excellentes.addWidget(
            self._entete_colonne(_("Excellentes — %s") % saison))
        for moment, groupes in armory.EXCELLENTES.get(cle, {}).items():
            # Il fait nuit sur Atys de 22 h a 3 h : dire laquelle des deux
            # listes vaut en ce moment evite d'aller forer ce qui ne sortira
            # que dans huit heures.
            actuel = (moment == "NUIT") == releve.nuit
            titre = _("De jour") if moment == "JOUR" else _("De nuit")
            if actuel:
                titre += _("  ·  en ce moment")
            pile = self._jour if moment == "JOUR" else self._nuit
            pile.addWidget(self._bloc_matieres(titre, groupes, True, actuel,
                                               qualite="excellent"))

    def _maj_entete(self, releve) -> None:
        maintenant = releve.maintenant()
        if maintenant is None:
            return
        suite = [c for c in releve.cycles_des_primes()
                 if c.cycle > releve.cycle_courant]
        prochain = next((c for c in suite
                         if c.condition != maintenant.condition), None)
        meilleur = next((c for c in suite if c.condition == "best"), None)

        # Chaque morceau est echappe pour lui-meme, et le gras pose ensuite :
        # echapper la phrase entiere puis remettre les balises a la main
        # marcherait, mais cederait au premier nom contenant un "&".
        def gras(texte: str) -> str:
            return f"<b>{html.escape(texte)}</b>"

        morceaux = [
            gras(f"{meteo.texte_meteo(maintenant.text)} · "
                 f"{int(maintenant.value * 100)} %"),
            html.escape("  →  "),
            gras(meteo.texte_condition(maintenant.condition)),
        ]
        if prochain is not None:
            morceaux.append(html.escape(
                f"   {meteo.texte_condition(prochain.condition)} dans "
                f"{meteo.duree(releve.minutes_avant(prochain.cycle))}"))
        # La fenetre excellente, sauf si elle est deja annoncee juste au-dessus.
        if (maintenant.condition != "best" and meilleur is not None
                and (prochain is None or meilleur.cycle != prochain.cycle)):
            morceaux.append(html.escape(
                "   ✦ Excellente dans "
                f"{meteo.duree(releve.minutes_avant(meilleur.cycle))}"))
        morceaux.append(html.escape(
            f"   ·   {meteo.nom_saison(releve.saison)}, "
            f"{releve.heure_du_jour} h sur Atys, "
            f"{'nuit' if releve.nuit else 'jour'}"))
        self._entete.setText("".join(morceaux))

    @staticmethod
    def _entete_colonne(titre: str) -> QWidget:
        lbl = QLabel(titre)
        lbl.setObjectName("peuple")
        lbl.setContentsMargins(0, 0, 0, 4)
        return lbl

    @staticmethod
    def _matieres_html(qualite: str, famille: str, matieres: list) -> str:
        """La liste des matières, celles qu'on sait situer devenant des liens.

        Un lien plutôt qu'un bouton : la liste garde son allure de phrase et
        continue de se replier toute seule quand la colonne rétrécit. Une
        matière sans carte reste du texte ordinaire — rien n'invite à cliquer
        sur ce qui ne répondrait pas.
        """
        morceaux = []
        for matiere in matieres:
            texte = html.escape(matiere)
            if gisements.points(qualite, famille, matiere):
                cible = html.escape(f"{qualite}|{famille}|{matiere}")
                morceaux.append(f'<a href="{cible}">{texte}</a>')
            else:
                morceaux.append(texte)
        return ", ".join(morceaux)

    def _on_gisement(self, adresse: str) -> None:
        page_gisements.montrer(self, *adresse.split("|", 2))

    def _bloc_matieres(self, titre: str, groupes: dict, zebre: bool,
                       souligne: bool = False,
                       qualite: str = "supreme") -> QWidget:
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
        entete.setObjectName("fini" if souligne else "titre")
        colonne.addWidget(entete)

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
            cellule.setFixedWidth(90)
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
                    TAILLE_SYMBOLE, Qt.TransformationMode.SmoothTransformation))
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

        colonne.addWidget(porteur)
        return boite
