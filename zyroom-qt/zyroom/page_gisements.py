"""Où sort une matière : nos propres marqueurs sur la carte d'Atys.

On embarquait autrefois les vues rendues par le tracker — trois mégaoctets
d'images figées. Ballistic Mystix a donné les coordonnées : sept kilooctets,
notre carte, et un zoom libre.

**Le nom du lieu est écrit aussi**, parce qu'un point ne dit pas où aller. Les
coordonnées, elles, ne le sont pas : le jeu ne permet pas de taper une position
pour y poser un repère, et deux nombres qu'on ne peut ni saisir ni recopier
nulle part n'apprennent rien.

**Les points ne se valent pas au même instant.** Une suprême sort dans une zone
des Primes et pas dans la voisine, selon le temps qu'il y fait : la carte les
montrait tous du même rouge, et il fallait retourner au tableau pour savoir
auquel aller. Ceux qui sortent en ce moment sont **verts**, les autres gris —
gris et non retirés, parce que « ici, mais pas maintenant » est une réponse, et
qu'une carte amputée n'en donne aucune.

**Et elle suit le temps.** Un cycle météo dure neuf minutes réelles : une carte
laissée ouverte mentait dès la bascule suivante, et elle mentait en silence.
Elle se recalcule au battement de l'écran météo — couleurs, décompte et
phrases — sans rien redemander à l'API.
"""
from __future__ import annotations

import html

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QGridLayout, QLabel, QVBoxLayout,
                               QWidget)

from . import carte, gisements, meteo
from .carte_widget import (POINT_ACTIF, POINT_INACTIF, CarteAtys, cible,
                           texte_cerne)
from .i18n import _

#: La qualité des gisements telle que la table de forage la nomme.
_QUALITE = {"supreme": meteo.SUPREME, "excellent": meteo.EXCELLENTE}

#: La part du cadre qu'occupe le semis de points au premier affichage.
CADRAGE = 0.55

#: En deca de cette distance a l'ecran, deux gisements n'en font qu'un : deux
#: points d'une meme zone tombent sur le meme pixel a l'echelle 1, et deux
#: noms superposes ne se lisent plus.
SEUIL_GROUPE = 40.0


def _releve_de(page):
    """Le relevé météo que tient l'écran d'où la carte a été ouverte."""
    return getattr(page, "_affiche", None) or getattr(page, "_releve", None)


def gisements_actifs(page, qualite: str, famille: str, matiere: str,
                     lieux: list):
    """Les lieux où cette matière sort en ce moment, et la météo du moment.

    Rend `(None, None)` quand on ne peut pas trancher — pas de relevé météo,
    ou des gisements hors des Primes, les seules zones dont la table de forage
    parle. Mieux vaut tout laisser au même ton que griser au hasard.
    """
    releve = _releve_de(page)
    actuelle = releve.maintenant() if releve is not None else None
    connus = [lieu for lieu in lieux if lieu in meteo.ZONES]
    if actuelle is None or not connus:
        return None, None
    attendue = _QUALITE.get(qualite)
    actifs = {lieu for lieu in lieux
              if lieu not in meteo.ZONES
              or meteo.qualite_de(lieu, famille, matiere,
                                  releve.saison, actuelle.condition)
              == attendue}
    return actifs, actuelle


def prochaine_sortie(page, qualite: str, famille: str, matiere: str,
                     lieux: list):
    """Le premier cycle à venir où cette matière sortira quelque part.

    Chaque matière a son propre créneau : dire « ça ne sort pas » sans dire
    quand, c'était obliger à retourner lire la courbe et à poser l'addition.
    On interroge la même table que pour le vert et le gris, cycle par cycle.
    """
    releve = _releve_de(page)
    if releve is None:
        return None
    attendue = _QUALITE.get(qualite)
    zones = [lieu for lieu in lieux if lieu in meteo.ZONES]
    for cycle in releve.cycles_des_primes():
        if cycle.cycle <= releve.cycle_courant:
            continue
        if any(meteo.qualite_de(lieu, famille, matiere, releve.saison,
                                cycle.condition) == attendue
               for lieu in zones):
            return releve.minutes_avant(cycle.cycle)
    return None


def textes_carte(page, qualite: str, famille: str, matiere: str, lieux: list):
    """Les lieux qui sortent, et les deux phrases qui l'expliquent.

    Un seul endroit pour les deux : l'ouverture de la fenêtre et le battement
    qui la rafraîchit doivent dire mot pour mot la même chose, sans quoi l'une
    des deux dériverait sans qu'on s'en aperçoive.
    """
    actifs, actuelle = gisements_actifs(page, qualite, famille, matiere, lieux)
    if actifs is None:
        return None, "", ""
    dehors = [lieu for lieu in lieux if lieu not in actifs]
    sortent = len(lieux) - len(dehors)
    maintenant = (
        (_("En ce moment — %(condition)s, %(taux)d %% : aucun des "
           "%(total)d gisements ne sort.") if not sortent
         else _("En ce moment — %(condition)s, %(taux)d %% : "
                "un gisement sur %(total)d.") if sortent == 1
         else _("En ce moment — %(condition)s, %(taux)d %% : "
                "%(sortent)d gisements sur %(total)d."))
        % {"condition": meteo.texte_condition(actuelle.condition),
           "taux": round(actuelle.value * 100),
           "sortent": sortent, "total": len(lieux)}
        + (_("  Les autres sont en gris.") if dehors and sortent else ""))
    apres = ""
    if not sortent:
        minutes = prochaine_sortie(page, qualite, famille, matiere, lieux)
        apres = (_("Prochaine fois dans %(delai)s — %(quand)s.")
                 % {"delai": meteo.duree(minutes),
                    "quand": meteo.moment_du_changement(minutes)}
                 if minutes is not None
                 else _("Pas avant six heures — au-delà, le jeu ne dit "
                        "plus le temps qu'il fera."))
    return actifs, maintenant, apres


def rafraichir_ouvertes(page) -> None:
    """Remet les cartes ouvertes à l'heure, au battement de l'écran météo.

    Un cycle dure neuf minutes réelles : une carte laissée ouverte mentait dès
    la bascule suivante, et elle mentait en silence — rien ne distingue un
    point vert juste d'un point vert périmé. Rien n'est redemandé à l'API :
    l'écran météo fait déjà avancer son relevé tout seul.
    """
    for ouverte in list(getattr(page, "_cartes_gisements", [])):
        actifs, maintenant, apres = textes_carte(
            page, ouverte["qualite"], ouverte["famille"], ouverte["matiere"],
            ouverte["lieux"])
        ouverte["carte"].poser_actifs(actifs)
        for label, texte in ((ouverte["maintenant"], maintenant),
                             (ouverte["apres"], apres)):
            label.setText(texte)
            label.setVisible(bool(texte))
        for lieu, label in ouverte["noms"].items():
            _ternir(label, actifs is not None and lieu not in actifs)


def _ternir(label: QLabel, terne: bool) -> None:
    """Le nom suit le point : terni quand le gisement ne sort pas.

    La feuille de style porte la regle `QLabel#compact[discret="true"]`, et Qt
    ne la relit pas tout seul quand la propriete change : il faut le depolir
    puis le repolir, sinon la couleur reste celle du premier affichage.
    """
    if label.property("discret") == terne:
        return
    label.setProperty("discret", terne)
    label.style().unpolish(label)
    label.style().polish(label)


class CarteGisements(CarteAtys):
    """La carte, cadrée sur les gisements dès qu'elle connaît sa taille."""

    def __init__(self, points: list, actifs=None) -> None:
        super().__init__(self._peindre, hauteur=340)
        self._points = points
        self._actifs = actifs
        self._cadre_fait = False

    def poser_actifs(self, actifs) -> None:
        """Les lieux qui sortent en ce moment. `None` : on ne sait pas."""
        if actifs == self._actifs:
            return
        self._actifs = actifs
        self.update()

    def _pixels(self) -> list:
        sortie = []
        for x, y, _lieu in self._points:
            point = carte.pixel(x, y)
            if point is not None:
                sortie.append(point)
        return sortie

    def _peindre(self, peintre, echelle: float, marge_x: float,
                 marge_y: float) -> None:
        # Le cadrage au premier dessin : avant, le widget n'a pas de taille.
        if not self._cadre_fait:
            self._cadre_fait = True
            self.cadrer(self._pixels(), CADRAGE)
            return                    # le cadrage a redemande un dessin

        vus: dict[tuple[int, int], list] = {}
        for x, y, lieu in self._points:
            point = carte.pixel(x, y)
            if point is None:
                continue
            px = marge_x + point[0] * echelle
            py = marge_y + point[1] * echelle
            cle = (int(px / SEUIL_GROUPE), int(py / SEUIL_GROUPE))
            if cle in vus:
                vus[cle][3] += 1
            else:
                vus[cle] = [px, py, lieu, 1]

        # Les gris d'abord, les verts par-dessus : deux gisements voisins se
        # recouvrent parfois d'un pixel, et c'est celui qui sort qu'on veut
        # voir.
        for vert in (False, True):
            for px, py, lieu, nombre in vus.values():
                if not (-40 <= px <= self.width() + 40
                        and -40 <= py <= self.height() + 40):
                    continue
                sort = self._actifs is None or lieu in self._actifs
                if sort != vert:
                    continue
                cible(peintre, px, py,
                      POINT_ACTIF if sort else POINT_INACTIF)
                texte_cerne(peintre, px + 11, py - 7,
                            lieu if nombre == 1 else f"{lieu} ×{nombre}")


def montrer(parent, qualite: str, famille: str, matiere: str) -> None:
    """Ouvre la carte des gisements d'une matière."""
    points = gisements.points(qualite, famille, matiere)
    if not points:
        return
    # Les lieux d'abord : l'en-tete en parle, et le trace les colore.
    lieux = list(dict.fromkeys(lieu for _x, _y, lieu in points))
    actifs, texte_maintenant, texte_apres = textes_carte(
        parent, qualite, famille, matiere, lieux)

    fen = QDialog(parent)
    fen.setWindowTitle(f"{matiere} — {famille}")
    # Quarante points de plus qu'avant : la ligne "en ce moment" s'ajoute sous
    # l'en-tete, et elle se replie sur deux lignes quand rien ne sort.
    fen.resize(720, 680)
    colonne = QVBoxLayout(fen)
    colonne.setContentsMargins(10, 10, 10, 10)
    colonne.setSpacing(10)

    mot = _("Suprême") if qualite == "supreme" else _("Excellente")
    fourchettes = gisements.humidites(qualite, famille, matiere)
    # Sans espace autour du tiret, et la virgule decimale du francais : deux
    # fourchettes doivent tenir sur la ligne du titre.
    humidite = ", ".join(f"{bas:g}–{haut:g} %".replace(".", ",")
                         for bas, haut in fourchettes)
    entete = QLabel(
        f"<b>{html.escape(mot)}</b>"
        + (f"  ·  {_('humidité')} {html.escape(humidite)}" if humidite else "")
        + f"  ·  {len(points)} "
        + (_("gisements") if len(points) > 1 else _("gisement")))
    entete.setWordWrap(True)
    colonne.addWidget(entete)

    # Ce que le vert et le gris veulent dire, ecrit une fois : un code de
    # couleur qu'il faut deviner ne vaut pas mieux que pas de code du tout.
    # Les deux etiquettes existent toujours, meme vides : le battement les
    # remplit et les vide, et une etiquette creee a la volee obligerait a
    # reconstruire la fenetre pour rien.
    etiquettes = []
    for texte in (texte_maintenant, texte_apres):
        lbl = QLabel(texte)
        lbl.setObjectName("compact")
        lbl.setWordWrap(True)
        lbl.setVisible(bool(texte))
        colonne.addWidget(lbl)
        etiquettes.append(lbl)

    vue = CarteGisements(points, actifs)
    colonne.addWidget(vue, 1)

    # Les lieux, sur deux colonnes : les gisements vont jusqu'a cinq lieux, et
    # une colonne unique repousserait l'attribution hors de la fenetre.
    porteur = QWidget()
    grille = QGridLayout(porteur)
    grille.setContentsMargins(0, 0, 0, 0)
    grille.setHorizontalSpacing(24)
    grille.setVerticalSpacing(2)
    grille.setColumnStretch(0, 1)
    grille.setColumnStretch(1, 1)
    rangs = max(1, (len(lieux) + 1) // 2)
    noms = {}
    for rang, lieu in enumerate(lieux):
        lbl = QLabel(lieu)
        lbl.setObjectName("compact")
        # Le nom suit le point : terni quand le gisement ne sort pas, pour
        # qu'on puisse lire la reponse dans la liste sans viser un pixel.
        _ternir(lbl, actifs is not None and lieu not in actifs)
        noms[lieu] = lbl
        grille.addWidget(lbl, rang % rangs, rang // rangs)
    colonne.addWidget(porteur)

    credit = QLabel(_("Positions : relevé de ballisticmystix.net, avec "
                      "l'accord de son auteur"))
    credit.setObjectName("discret")
    credit.setWordWrap(True)
    colonne.addWidget(credit)

    # La fenetre s'inscrit au battement de l'ecran meteo, et s'en retire en se
    # fermant : une carte fermee qu'on continuerait de redessiner planterait a
    # la premiere bascule de cycle.
    ouverte = {"qualite": qualite, "famille": famille, "matiere": matiere,
               "lieux": lieux, "carte": vue, "noms": noms,
               "maintenant": etiquettes[0], "apres": etiquettes[1]}
    ouvertes = getattr(parent, "_cartes_gisements", None)
    if ouvertes is None:
        ouvertes = parent._cartes_gisements = []
    ouvertes.append(ouverte)
    fen.finished.connect(
        lambda _code: ouverte in ouvertes and ouvertes.remove(ouverte))
    # `WA_DeleteOnClose`, sans quoi le QDialog survit a sa fermeture et le
    # battement continuerait de peindre dans une fenetre invisible.
    fen.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

    # Non modale : on compare volontiers deux matieres cote a cote.
    fen.setModal(False)
    fen.show()
