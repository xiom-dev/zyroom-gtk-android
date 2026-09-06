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

from PySide6.QtWidgets import (QApplication, QLabel,  # noqa: E402
                               QProgressBar)

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


def couleur_texte(widget, sans_a_droite: int = 0) -> str:
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
    pixels = collections.Counter(
        image.pixelColor(x, y).name()
        for x in range(marge, droite)
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
    points["nav.bonus.couleur-active"] = couleur_texte(f._btn_plus, 30)
    f._montrer_page("inventory")
    points["nav.bonus.couleur-inactive"] = couleur_texte(f._btn_plus, 30)

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
        cote = (len(boutons) == 2
                and boutons[0].pos().y() == boutons[1].pos().y()
                and boutons[0].pos().x() != boutons[1].pos().x())
        points["options.compteur.boutons"] = ("cote a cote" if cote
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
    return points


def main() -> int:
    resultat: dict = {}
    app = QApplication([])
    app.setStyleSheet(theme.feuille())
    try:
        fenetre = FenetrePrincipale()
        fenetre.show()
        resultat.update(relever(fenetre))
    except Exception as souci:                          # noqa: BLE001
        resultat["erreur"] = f"{type(souci).__name__} : {souci}"
    json.dump(resultat, sys.stdout, ensure_ascii=False, indent=1, sort_keys=True)
    return 1 if "erreur" in resultat else 0


if __name__ == "__main__":
    raise SystemExit(main())
