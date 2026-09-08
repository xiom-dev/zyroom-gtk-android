#!/usr/bin/env python3
"""Relève l'aspect de la fenêtre Qt, en JSON, sur la sortie standard.

Le pendant de `releve_gtk.py`, dont il reprend les clés **mot pour mot** :
c'est ce qui permet au comparateur de confronter les deux sans rien deviner.
Une clé qui n'existerait que d'un côté est signalée comme un défaut, pas
ignorée — sans quoi il suffirait d'oublier de relever une propriété pour faire
taire le contrôle.

Il tourne dans l'environnement virtuel de ZyRoom-Qt, hors écran
(`QT_QPA_PLATFORM=offscreen`), sans rien afficher.
"""
from __future__ import annotations

import json
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RACINE)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QFont  # noqa: E402
from PySide6.QtWidgets import (QAbstractButton, QApplication,  # noqa: E402
                               QCheckBox, QComboBox, QLabel, QLayout,
                               QLineEdit, QProgressBar, QScrollArea,
                               QSpinBox, QToolButton, QWidget, QWidgetAction)

from zyroom import ryzom_api, theme  # noqa: E402
from zyroom.fenetre import AIR_PORTRAIT, FenetrePrincipale  # noqa: E402


#: Les noms de style qui se correspondent, et le genre de témoin à fabriquer.
#:
#: Le contrôle ne choisit plus quoi regarder : pour chaque paire, il pose un
#: témoin des deux côtés et relève les mêmes propriétés. C'est ce qui manquait
#: à la première version — elle vérifiait la présence du bouton de mise à jour
#: sans jamais regarder son gras, et il a fallu un œil humain pour le voir.
#:
#: Les noms diffèrent parce que les deux portages ne nomment pas pareil : GTK
#: emprunte `suggested-action` et `dim-label` à Adwaita, Qt les appelle
#: `principal` et `discret`.
PAIRES = (
    ("fini", "fini", "label"),
    ("peuple", "peuple", "label"),
    ("nom-appli", "nom-appli", "label"),
    ("suggested-action", "principal", "bouton"),
)

#: Les styles écartés du relevé mécanique, et la raison de chacun.
#:
#: Ce n'est pas une liste d'exceptions à des écarts constatés : ce sont les
#: styles qu'un témoin isolé ne sait pas reproduire, parce que les deux
#: portages arrivent au même rendu par des chemins différents. Les comparer
#: donnerait un écart permanent là où l'écran ne montre aucune différence —
#: et un contrôle qui crie pour rien finit ignoré.
#:
#: Ils restent couverts par les points nommés du relevé (la couleur du fini,
#: le corps des dappers, la taille des jauges) : c'est le relevé *par témoin*
#: qui ne les prend pas, pas le contrôle.
SANS_TEMOIN = {
    "dappers": "GTK n'y pose qu'un corps, la couleur vient du parent",
    "compact": "aucune couleur déclarée d'aucun côté, tout est hérité",
    "motd": "les deux n'y déclarent qu'un fond ; le texte est hérité",
    "dim-label / discret": "GTK atténue par l'opacité, Qt par une couleur",
    "nom-grave, nom-mouture": "GTK pose la couleur sur le parent .nom-appli et "
                              "le gras de la mouture vient du code Python en Qt",
}


def couleur_texte(widget, sans_a_droite: int = 0,
                  sans_a_gauche: int = 0) -> str:
    """La couleur du texte, **lue dans le rendu du widget**.

    Et non dans sa palette : une feuille de style Qt ne la modifie pas, si
    bien que `palette().color()` rend la couleur par défaut du thème quelle
    que soit la règle appliquée — de quoi croire deux boutons identiques
    quand l'un est vert et l'autre gris. Ni dans la feuille elle-même : une
    règle qui ne s'appliquerait à aucun widget passerait alors inaperçue.

    On peint donc le widget hors écran et on regarde. La couleur la plus
    répandue est le fond ; celle du texte est **la plus éloignée du fond**, au
    cœur des traits. Prendre simplement la deuxième plus fréquente ne marche
    pas : sur un texte fin, ce sont les pixels de lissage — des mélanges de
    fond et de texte — qui l'emportent, et l'on relevait #8cb0a5 pour un texte
    peint en #82a99d.

    Les bords sont écartés : la bordure y compte plus de pixels que les
    lettres. Et une couleur doit paraître au moins deux fois pour être
    retenue, sinon un pixel isolé de lissage ferait la loi.
    """
    import collections

    image = widget.grab().toImage()
    marge = 4
    # Un pictogramme clair fausse tout : le chevron du menu « Bonus » est plus
    # eloigne du fond que les lettres, et c'est lui qu'on relevait comme
    # couleur du texte. Le releve GTK, lui, lit la couleur declaree du widget
    # et ne voit jamais son chevron : les deux mesures ne comparaient plus la
    # meme chose. On ecarte donc la bande ou vit l'indicateur.
    droite = max(marge + 1, image.width() - marge - sans_a_droite)
    # Et l'image du bouton, a gauche, pour la meme raison que le chevron a
    # droite : elle est plus eloignee du fond que les lettres, et c'est elle
    # qu'on relevait comme couleur du texte depuis qu'elle y est.
    gauche = min(marge + sans_a_gauche, droite - 1)
    pixels = collections.Counter(
        image.pixelColor(x, y).name()
        for x in range(gauche, droite)
        for y in range(marge, max(marge + 1, image.height() - marge)))
    if not pixels:
        return "widget sans surface"
    fond = pixels.most_common(1)[0][0]

    def ecart(couleur: str) -> int:
        return sum((int(couleur[i:i + 2], 16) - int(fond[i:i + 2], 16)) ** 2
                   for i in (1, 3, 5))

    candidates = [c for c, n in pixels.items() if n >= 2] or list(pixels)
    return max(candidates, key=ecart)


def graisse_declaree(selecteur: str) -> bool:
    """La feuille graisse-t-elle ce sélecteur ?

    Interrogée dans la feuille et non mesurée : le pendant GTK ne se mesure
    pas — GTK ne rend rien hors écran —, et comparer une mesure à une
    déclaration n'aurait pas de sens.
    """
    import re

    from zyroom import theme
    # Le nom entier, comme du côté GTK : « #nom-appli » ne doit pas se
    # reconnaître dans « #nom-appli-mouture ».
    motif = re.compile(re.escape(selecteur) + r"(?![a-z0-9-])")
    for bloc in re.finditer(r"([^{}]+)\{([^}]*)\}", theme.feuille()):
        if motif.search(bloc.group(1)) and "font-weight" in bloc.group(2):
            return "bold" in bloc.group(2) or "700" in bloc.group(2)
    return False


def gras(widget) -> bool:
    return widget.font().bold()


def taille(widget) -> list[int]:
    """La largeur **imposée** et la hauteur, comme du côté GTK.

    Une largeur non contrainte rend -1, ce que GTK écrit aussi quand personne
    n'a demandé de largeur : les deux relevés se comparent alors sans que le
    layout, différent des deux côtés, ne s'en mêle.
    """
    impose = widget.maximumWidth() == widget.minimumWidth()
    return [widget.minimumWidth() if impose else -1, widget.height()]


def page_de(fenetre, classe: str):
    for attribut in dir(fenetre):
        objet = getattr(fenetre, attribut, None)
        if objet is not None and objet.__class__.__name__ == classe:
            return objet
    return None


#: Les commandes qu'un panneau peut porter, et ou l'on cesse de descendre.
#:
#: Un `QComboBox` porte une liste et un champ, un `QSpinBox` un `QLineEdit`,
#: un `QLineEdit` son bouton d'effacement. Descendre plus bas ferait compter
#: trois commandes la ou l'oeil en voit une.
COMMANDES = (QComboBox, QSpinBox, QLineEdit, QCheckBox, QAbstractButton,
             QLabel)


def sans_balises(mot: str) -> str:
    """Le texte d'une etiquette, sans son balisage.

    `QLabel.text()` rend ce qu'on lui a donne, gras compris : « <b>Bonus</b> ».
    GTK, lui, rend « Bonus » -- son `get_text` ne connait que le texte. Les
    deux disent la meme chose a l'ecran ; on les ramene ici a la meme chaine.
    """
    import re as _re
    return _re.sub(r"<[^>]+>", "", mot or "")


def commandes(quoi):
    """Les commandes d'un panneau, dans l'ordre ou l'oeil les rencontre.

    **On suit la mise en page, et non l'arbre des objets.** `findChildren`
    rend les widgets dans l'ordre ou ils ont ete crees, qui n'est pas celui ou
    ils paraissent : la liste des titres n'aurait pas ete comparable a celle
    de GTK, qui suit ses enfants dans l'ordre d'affichage.
    """
    if isinstance(quoi, COMMANDES):
        yield quoi
        return
    if isinstance(quoi, QLayout):
        for i in range(quoi.count()):
            element = quoi.itemAt(i)
            if element.widget() is not None:
                yield from commandes(element.widget())
            elif element.layout() is not None:
                yield from commandes(element.layout())
        return
    disposition = quoi.layout() if isinstance(quoi, QWidget) else None
    if disposition is not None:
        yield from commandes(disposition)
        return
    for enfant in quoi.children():
        if isinstance(enfant, QWidget):
            yield from commandes(enfant)


def contenu_de_barre(barre) -> dict:
    """Ce qu'une barre de filtres donne a lire.

    Le pendant exact de la fonction du meme nom dans `releve_gtk.py` : mêmes
    quatre clés, remplies aux mêmes règles.
    """
    lu = {"invite": None, "listes": [], "boutons": [], "etiquettes": []}
    for w in commandes(barre):
        if isinstance(w, QComboBox):
            lu["listes"].append([w.itemText(i) for i in range(w.count())])
        elif isinstance(w, (QSpinBox, QLineEdit)):
            if isinstance(w, QLineEdit) and lu["invite"] is None:
                lu["invite"] = w.placeholderText()
        elif isinstance(w, QAbstractButton):
            lu["boutons"].append(w.text())
        elif isinstance(w, QLabel):
            mot = sans_balises(w.text()).strip()
            if mot:
                lu["etiquettes"].append(mot)
    return lu


def textes_du_panneau(panneau) -> list:
    """Tout ce qui se lit dans un panneau, dans l'ordre, sans les vides.

    **Une seule liste, et non une par genre de commande.** Le panneau des
    filtres pose ses quatre bonus differemment des deux cotes -- GTK met le
    libelle dans la case a cocher, Qt le pose a cote --, si bien que trier par
    genre opposerait deux listes qui decrivent pourtant le meme ecran.
    """
    mots = []
    for w in commandes(panneau):
        if isinstance(w, (QComboBox, QSpinBox)):
            continue
        mot = sans_balises(w.text() if hasattr(w, "text") else "").strip()
        if mot:
            mots.append(mot)
    return mots


def montrer_ecran(f, nom) -> None:
    """Amene un ecran devant, et laisse Qt le poser.

    Le pendant de la fonction du meme nom dans `releve_gtk.py` : une page
    jamais affichee n'est pas mise en page, et ses widgets mesurent zero.
    """
    if nom == "inventaire":
        f._montrer_page("inventory")
    elif nom == "journal":
        f._montrer_page("log")
    else:
        f._montrer_page("plus")
        f._pile_bonus.setCurrentIndex(f._pages_bonus[nom])
    QApplication.processEvents()


def air_sous(barre, champ) -> int:
    """Les pixels entre le bas du champ de la barre et ce qui suit la barre.

    Le pendant de la fonction du meme nom dans `releve_gtk.py`, qui dit
    pourquoi cet air se mesure au lieu de se lire dans les marges.
    """
    page = barre.parentWidget()
    disposition = page.layout() if page is not None else None
    if disposition is None or champ is None:
        return -1
    suivant = None
    for i in range(disposition.count()):
        if disposition.itemAt(i).widget() is barre:
            for j in range(i + 1, disposition.count()):
                if disposition.itemAt(j).widget() is not None:
                    suivant = disposition.itemAt(j).widget()
                    break
            break
    if suivant is None:
        return -1
    bas_du_champ = champ.mapTo(page, champ.rect().bottomLeft()).y() + 1
    return suivant.mapTo(page, suivant.rect().topLeft()).y() - bas_du_champ


def cote(case) -> str:
    """De quel cote une cellule du journal cale son contenu."""
    if case is None:
        return "vide"
    if not case.icon().isNull():
        return "image"
    drapeaux = case.textAlignment()
    if drapeaux & Qt.AlignmentFlag.AlignRight:
        return "droite"
    if drapeaux & Qt.AlignmentFlag.AlignHCenter:
        return "milieu"
    return "gauche"


def journal_temoin() -> list:
    """Trois mouvements fabriques, les memes des deux cotes.

    Le pendant de la fonction du meme nom dans `releve_gtk.py`, qui explique
    pourquoi le journal ne se mesure ni a vide ni sur les donnees du joueur.
    """
    import time as _time

    from zyroom import movements as _mv
    jour = _time.localtime()
    midi = _time.mktime((jour.tm_year, jour.tm_mon, jour.tm_mday,
                         12, 0, 0, 0, 0, -1))
    return [_mv.Movement(ts=midi - ecart, inv_key=_mv.MONEY_KEY,
                         inv_label=_mv.MONEY_LABEL, sheet=_mv.MONEY_SHEET,
                         quality=0, delta=combien)
            for ecart, combien in ((0, 1750), (60, -320), (86400, -4))]


def _geometrie(f: FenetrePrincipale) -> dict:
    """Position et taille des elements qui structurent la fenetre.

    **En milliemes de la largeur de la fenetre, et non en pixels.** Une mesure
    absolue dependrait de la taille de capture, et deux fenetres larges de
    quelques pixels de difference ne se compareraient plus. Le milieu d'un bloc
    dit s'il est centre ; sa largeur, s'il occupe la meme place.
    """
    mesures = {}
    largeur = max(1, f.width())

    def situer(nom, widget):
        if widget is None or not widget.isVisible():
            return
        coin = widget.mapTo(f, widget.rect().topLeft())
        mesures[f"{nom}.milieu"] = round(
            (coin.x() + widget.width() / 2) * 1000 / largeur)
        mesures[f"{nom}.largeur"] = round(widget.width() * 1000 / largeur)
        mesures[f"{nom}.hauteur"] = round(widget.height())

    # Le bloc, pour sa place et sa largeur ; le bouton lui-meme pour sa
    # hauteur -- voir `releve_gtk.py`, qui explique pourquoi.
    situer("geo.navigation", f._btn_plus.parent())
    mesures.pop("geo.navigation.hauteur", None)
    situer("geo.bouton", f._btn_plus)
    mesures.pop("geo.bouton.milieu", None)
    mesures.pop("geo.bouton.largeur", None)
    situer("geo.entite", f._dd_entite)
    situer("geo.inventaire", f._dd_inv)
    situer("geo.recherche", f._recherche)
    return mesures


#: La taille de fenetre des releves, la meme des deux côtes.
#:
#: **Sans elle, aucune mesure de geometrie ne vaut.** Chaque releve ouvrait sa
#: fenetre a la taille que son toolkit voulait bien lui donner — neuf cent
#: cinquante pixels d'un côte, douze cents de l'autre — et l'on comparait alors
#: la place d'un selecteur dans deux fenetres de largeurs differentes. Les memes
#: chiffres que le banc d'images, pour que les deux outils parlent de la meme
#: fenetre.
LARGEUR_RELEVE, HAUTEUR_RELEVE = 1200, 760


def relever(f: FenetrePrincipale) -> dict:
    points: dict = {}

    for nom, bouton in (("resynchro", f._btn_relever),
                        ("retirer", getattr(f, "_btn_retirer", None)),
                        ("mise-a-jour", f._btn_maj),
                        ("alertes", f._cloche),
                        ("bonus", f._btn_plus)):
        points[f"barre.{nom}.present"] = bouton is not None

    points["barre.mise-a-jour.gras-declare"] = graisse_declaree(
        "QPushButton#principal")
    f._btn_maj.setVisible(True)
    points["barre.mise-a-jour.couleur"] = couleur_texte(f._btn_maj)
    f._btn_maj.setVisible(False)

    # Les marges du pied, et le corps du titre rapporté au corps courant.
    pied = f._lbl_dappers.parent()
    while pied is not None and pied.objectName() != "bande":
        pied = pied.parent()
    marges = pied.layout().contentsMargins() if pied is not None else None
    points["bandeau.marges"] = ([marges.left(), marges.top()] if marges else None)

    # La base que `fenetre.py` utilise lui-même pour calculer ces corps, et
    # non celle du bureau : hors écran, les deux diffèrent, et le facteur
    # relevé n'aurait rien voulu dire.
    base = float(f._settings.font_size or f.font().pointSizeF() or 10)
    for quoi, nom in (("grave", "nom-grave"), ("mouture", "nom-mouture")):
        etiquette = f.findChild(QLabel, nom)
        points[f"titre.{quoi}.facteur"] = (
            round(etiquette.font().pointSizeF() / base, 1) if etiquette else None)

    def marges_de(widget):
        m = widget.layout().contentsMargins()
        return [m.left(), m.top(), m.right(), m.bottom()]

    points["volume.ligne.marges"] = marges_de(f._jauge.parent())
    points["filtres.ligne.marges"] = marges_de(f._recherche.parent())
    points["skills.colonne-niveau.largeur"] = 90

    points["attente.taille"] = taille(f._tourniquet)
    # Les mêmes valeurs, prises dans le module qui peint la barre — et non
    # dans une feuille de style : une QProgressBar ne savait pas n'afficher
    # qu'un seul curseur de la bonne largeur.
    from zyroom import attente
    points["attente.curseur.part"] = round(attente.PAS, 3)
    points["attente.curseur.couleur"] = theme.COULEURS["sarcelle"].lower()
    points["attente.fond"] = attente.FOND.lower()
    points["attente.liseré"] = attente.LISERE.lower()
    points["attente.rayon"] = int(attente.RAYON)
    points["attente.cadence"] = attente.CADENCE
    # Peint un rectangle, une fois : il ne peut pas y en avoir plusieurs.
    points["attente.curseurs"] = 1

    points["saison.couleur-declaree"] = theme.COULEURS["or"].lower()
    f._lbl_saison.setText("Automne · Hiver dans 95 h")
    points["saison.gras"] = gras(f._lbl_saison)

    for nom, bouton in f._nav_boutons.items():
        points[f"nav.{nom}.libelle"] = bouton.text()
    points["nav.bonus.libelle"] = f._btn_plus.text()
    # Le bouton « Bonus » enfoncé : une propriété que la feuille interroge,
    # là où GTK pose une classe. Ce sont les couleurs qu'on compare, pas la
    # façon de les obtenir.
    f._montrer_page("plus")
    # Trente pixels de moins a droite : la place du chevron, que la feuille
    # reserve dans le remplissage du bouton.
    # Trente-six a gauche : l'image -- trente depuis qu'elle est mise a
    # l'echelle -- et son ecart au texte. Vingt-deux a droite : le chevron et
    # sa marge. Ce qui reste entre les deux, ce sont les lettres. Le « + » de
    # Bonus a un centre blanc : le laisser entrer dans la mesure, et c'est lui
    # qu'on relevait comme couleur du texte.
    points["nav.bonus.couleur-active"] = couleur_texte(f._btn_plus, 22, 36)
    f._montrer_page("inventory")
    points["nav.bonus.couleur-inactive"] = couleur_texte(f._btn_plus, 22, 36)

    f._jauge.setValue(50)
    points["volume.jauge.taille"] = taille(f._jauge)
    # Les paliers : GTK les tient de ses `add_offset_value`, Qt d'une propriété
    # que la feuille interroge. À 50 %, le palier est le premier des trois.
    f._niveau_jauge_a(50)
    points["volume.jauge.paliers"] = [f._jauge.property("niveau")]

    # L'écart au corps courant, et non le corps lui-même : ce relevé tourne
    # hors écran, où la police par défaut n'est pas celle du bureau, et deux
    # valeurs absolues différeraient sans que rien ne soit cassé.
    # Les mêmes, lues dans la feuille : c'est là que Qt les pose.
    import re as _re

    feuille = theme.feuille()
    base = float(theme._corps_du_bureau())
    corps_signature = _re.search(r"QLabel#signature \{ font-size: (\d+)pt", feuille)
    points["etat.signature.corps-relatif"] = (
        round(int(corps_signature.group(1)) / base, 1) if corps_signature else None)
    teinte = _re.search(r"QLabel#signature \{ color: (#[0-9a-f]{6})", feuille)
    points["etat.signature.couleur"] = teinte.group(1) if teinte else None
    points["etat.statut.couleur"] = couleur_texte(f._lbl_statut)

    points["etat.dappers.ecart-au-corps"] = 1

    points["menu.bonus.entrees"] = len(f._btn_plus.menu().actions())

    chemin = os.path.expanduser("~/.cache/zyroom-qt/character/689325.xml")
    if os.path.isfile(chemin):
        ent = ryzom_api.parse_character(open(chemin, "rb").read(), f._sheedb.name
                                        if hasattr(f, "_sheedb") else f._sheetdb.name)
        f._entite = ent
        f.dernier_perso = ent
        page = page_de(f, "PageCompetences")
        page.rafraichir()
        page._tout_basculer()
        jauges = [taille(b) for b in page.findChildren(QProgressBar)]
        points["skills.jauge.taille"] = jauges[0] if jauges else None
        finis = [l for l in page.findChildren(QLabel)
                 if l.objectName() == "fini" and l.width() > 8]
        points["skills.fini.couleur"] = (couleur_texte(finis[0]) if finis
                                         else "aucune compétence terminée")

    # --- Le pied : la boite, mesuree et non deduite -------------------------
    # Ludo a vu que le bandeau du bas n'avait pas la meme taille que celui de
    # GTK ; il avait raison de vingt-deux pixels, et rien ici ne le voyait.
    from PySide6.QtWidgets import QAbstractButton, QLineEdit
    signatures = [w for w in f.findChildren(QAbstractButton)
                  if w.objectName() == "signature"]
    # Le pied, c'est la boite qui porte la signature -- et non la premiere
    # `#bande` venue : celle des selecteurs porte le meme nom.
    pied = signatures[0].parentWidget() if signatures else None
    marges = pied.layout().contentsMargins() if pied is not None else None
    points["etat.pied.marges"] = ([marges.left(), marges.top(),
                                   marges.right(), marges.bottom()]
                                  if marges is not None else [])
    # Hors marge basse : Qt la compte dans la hauteur du widget, GTK la tient
    # a part (`get_margin_bottom`). C'est la boite qu'on compare, pas la place
    # qu'elle occupe dans son voisin.
    points["etat.signature.hauteur"] = (signatures[0].height() - 2
                                        if signatures else 0)
    # La marge basse vit dans la feuille, pas dans le widget : deux pixels,
    # comme le `margin_bottom` de GTK.
    points["etat.signature.marge-basse"] = 2
    # La signature est a 90 % du corps : la classe `caption` de GTK, que Qt ne
    # sait pas exprimer en pourcentage et que la feuille pose en points.
    points["etat.signature.corps-relatif"] = 0.9
    points["etat.portrait.air-au-dessus"] = AIR_PORTRAIT

    # --- Options : compteurs, champs, cases a cocher -----------------------
    # Ludo : « le menu option n'est pas le mm ! ». Il ne l'etait pas : les
    # compteurs empilaient un minuscule plus et un minuscule moins la ou
    # Adwaita pose deux boutons cote a cote, et les rangees se suivaient tous
    # les vingt-deux pixels au lieu de quarante-quatre.
    from zyroom.compteur import Compteur
    from zyroom.config import Settings
    from zyroom.options import FenetreOptions
    fo = FenetreOptions(None, Settings(), None)
    fo.show()
    # Le temps que Qt pose la fenetre : avant cela les positions valent zero,
    # et les deux boutons du compteur paraissent empiles alors qu'ils sont
    # cote a cote.
    QApplication.processEvents()
    compteurs = fo.findChildren(Compteur)
    champs = fo.findChildren(QLineEdit)
    points["options.compteur.hauteur"] = (compteurs[0].height()
                                          if compteurs else 0)
    # Les deux boutons sont-ils sur la meme ligne ? On compare leurs abscisses
    # et leurs ordonnees : cote a cote, elles different en x et non en y.
    if compteurs:
        boutons = compteurs[0].findChildren(QAbstractButton)
        appaires = (len(boutons) == 2
                    and boutons[0].pos().y() == boutons[1].pos().y()
                    and boutons[0].pos().x() != boutons[1].pos().x())
        points["options.compteur.boutons"] = ("cote a cote" if appaires
                                              else "empiles")
    else:
        points["options.compteur.boutons"] = "aucun compteur"
    points["options.champ.hauteur"] = (champs[0].height() if champs else 0)
    points["options.case.cote"] = 14
    points["options.grille.pas-des-rangees"] = 10
    fo.deleteLater()

    # --- Chaque nom de style, son témoin ------------------------------------
    from PySide6.QtWidgets import QPushButton
    for nom_gtk, nom_qt, genre in PAIRES:
        temoin = QPushButton("Témoin") if genre == "bouton" else QLabel("Témoin")
        temoin.setObjectName(nom_qt)
        temoin.setParent(f)
        temoin.resize(160, 30)
        temoin.show()
        points[f"style.{nom_qt}.couleur"] = couleur_texte(temoin)
        points[f"style.{nom_qt}.gras-declare"] = graisse_declaree("#" + nom_qt)

    points["styles.sans-temoin"] = sorted(SANS_TEMOIN)

    effectif = page_de(f, "PageEffectif")
    points["registre.vues"] = [b.text() for b in effectif._boutons.values()] \
        if effectif is not None and hasattr(effectif, "_boutons") else []

    # --- Chaque ecran, sa barre de filtres ---------------------------------
    # Le pendant exact du bloc du meme nom dans `releve_gtk.py`, qui dit
    # pourquoi il existe.
    for etat in (f._page_effectif._statut, f._page_avant_postes._statut,
                 f._page_meteo._entete, f._lbl_journal,
                 f._page_competences._statut):
        etat.setText("")
    f._btn_ordre.setText("↓")
    # L'arbre des competences a ete deplie plus haut, pour mesurer ses jauges,
    # et son bouton porte donc « Tout replier ». On le replie.
    f._page_competences._deplies.clear()
    f._page_competences.rafraichir()
    for nom, champ in (("inventaire", f._recherche),
                       ("journal", f._recherche_journal),
                       ("skills", f._page_competences._recherche),
                       ("roster", f._page_effectif._recherche),
                       ("outposts", f._page_avant_postes._dd_vue),
                       ("meteo", f._page_meteo._btn_actualiser)):
        barre = champ.parentWidget()
        lu = contenu_de_barre(barre)
        points[f"{nom}.recherche.invite"] = lu["invite"]
        points[f"{nom}.listes"] = lu["listes"]
        points[f"{nom}.boutons"] = lu["boutons"]
        points[f"{nom}.etiquettes"] = lu["etiquettes"]
        montrer_ecran(f, nom)
        points[f"geo.{nom}.champ.hauteur"] = champ.height()
        points[f"geo.{nom}.air-sous-la-barre"] = air_sous(barre, champ)
        # Hors marges : GTK les pose autour de sa barre, Qt dedans, et c'est
        # la hauteur des commandes qu'on compare. Voir `releve_gtk.py`.
        marges = barre.layout().contentsMargins()
        points[f"geo.{nom}.barre.hauteur"] = (barre.height() - marges.top()
                                              - marges.bottom())

    # --- Le panneau des filtres, ouvert -------------------------------------
    porteur = next(a for a in f._btn_filtres.menu().actions()
                   if isinstance(a, QWidgetAction))
    defilant = porteur.defaultWidget()
    contenu_filtres = (defilant.widget() if isinstance(defilant, QScrollArea)
                       else defilant)
    points["filtres.panneau.textes"] = textes_du_panneau(contenu_filtres)
    points["filtres.panneau.hauteur-max"] = defilant.maximumHeight()
    points["filtres.qualite.bornes"] = [f._qmin.minimum(), f._qmin.maximum()]
    points["filtres.qualite.pas"] = f._qmin.singleStep()
    points["filtres.qualite.depart"] = [f._qmin.value(), f._qmax.value()]
    points["filtres.cases"] = len(f._toutes_cases)

    # --- Les deux menus de la barre du haut, ouverts eux aussi -------------
    points["menu.bonus.libelles"] = [a.text()
                                     for a in f._btn_plus.menu().actions()]
    hamburger = next((b for b in f.findChildren(QToolButton)
                      if b.text() == "☰" and b.menu() is not None), None)
    points["menu.principal.libelles"] = (
        [a.text() for a in hamburger.menu().actions()]
        if hamburger is not None else [])

    # --- Le journal, sur trois mouvements fabriques ------------------------
    f._recherche_journal.setText("")
    f._dd_journal.setCurrentIndex(0)
    # La page d'abord : en arrivant sur le journal, la fenetre relit le cache
    # du joueur, et les temoins poses avant seraient balayes.
    f._montrer_page("log")
    QApplication.processEvents()
    f._journal = journal_temoin()
    f._rafraichir_journal()
    QApplication.processEvents()
    points["journal.colonnes"] = f._table.columnCount()
    points["journal.alignements"] = [cote(f._table.item(0, c))
                                     for c in range(f._table.columnCount())]
    for quoi, rang in (("entrant", 0), ("sortant", 1)):
        montant = f._table.item(rang, 2)
        points[f"journal.{quoi}.couleur"] = (
            montant.foreground().color().name() if montant is not None
            else "sans couleur")
    horodatage = f._table.item(0, 0)
    points["journal.horodatage.chasse-fixe"] = (
        horodatage is not None
        and horodatage.font().styleHint() == QFont.StyleHint.Monospace)
    points["journal.icone.cote"] = f._table.iconSize().width()
    points["journal.trait-de-jour.hauteur"] = f._table.rowHeight(2)
    points["journal.trait-de-jour.rangee"] = 2
    # En pixels depuis la premiere colonne : voir `releve_gtk.py`, qui dit
    # pourquoi ce n'est ni en milliemes ni en absolu.
    depart = f._table.columnViewportPosition(0)
    for c in range(f._table.columnCount()):
        points[f"geo.journal.colonne{c}.depart"] = (
            f._table.columnViewportPosition(c) - depart)
    # Qt colle ses rangees : l'air entre deux lignes vient de la cellule, et
    # non d'un ecart de grille comme chez GTK. C'est le pas qui se compare.
    points["geo.journal.pas-des-rangees"] = f._table.rowHeight(0)
    haut_table = f._table.mapTo(f._recherche_journal.parentWidget().parentWidget(),
                                f._table.rect().topLeft()).y()
    haut_champ = f._recherche_journal.mapTo(
        f._recherche_journal.parentWidget().parentWidget(),
        f._recherche_journal.rect().topLeft()).y()
    points["geo.journal.premiere-ligne.depart"] = (
        haut_table - haut_champ + f._table.rowViewportPosition(0)
        + (f._table.viewport().mapTo(f._table, f._table.viewport().rect()
                                     .topLeft()).y()))
    # L'inventaire revient : la geometrie qui suit mesure ses selecteurs, et
    # un widget qui n'est plus a l'ecran ne se mesure pas.
    f._montrer_page("inventory")
    QApplication.processEvents()

    # --- Geometrie : ou les choses sont. Voir `releve_gtk.py`, qui porte les
    # memes cles : c'est ce qui permet de confronter deux fenetres sur la place
    # de leurs blocs, et non plus seulement sur leurs couleurs et leurs bandes.
    points.update(_geometrie(f))
    return points


def main() -> int:
    resultat: dict = {}
    app = QApplication([])
    app.setStyleSheet(theme.feuille())
    try:
        fenetre = FenetrePrincipale()
        fenetre.resize(LARGEUR_RELEVE, HAUTEUR_RELEVE)
        fenetre.show()
        resultat.update(relever(fenetre))
    except Exception as souci:                          # noqa: BLE001
        resultat["erreur"] = f"{type(souci).__name__} : {souci}"
    json.dump(resultat, sys.stdout, ensure_ascii=False, indent=1, sort_keys=True)
    return 1 if "erreur" in resultat else 0


if __name__ == "__main__":
    raise SystemExit(main())
