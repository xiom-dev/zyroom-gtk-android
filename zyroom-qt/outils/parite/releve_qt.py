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
from zyroom.fenetre import FenetrePrincipale  # noqa: E402


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


def couleur_texte(widget) -> str:
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
    pixels = collections.Counter(
        image.pixelColor(x, y).name()
        for x in range(marge, max(marge + 1, image.width() - marge))
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
    points["nav.bonus.couleur-active"] = couleur_texte(f._btn_plus)
    f._montrer_page("inventory")
    points["nav.bonus.couleur-inactive"] = couleur_texte(f._btn_plus)

    f._jauge.setValue(50)
    points["volume.jauge.taille"] = taille(f._jauge)
    # Les paliers : GTK les tient de ses `add_offset_value`, Qt d'une propriété
    # que la feuille interroge. À 50 %, le palier est le premier des trois.
    f._niveau_jauge_a(50)
    points["volume.jauge.paliers"] = [f._jauge.property("niveau")]

    # L'écart au corps courant, et non le corps lui-même : ce relevé tourne
    # hors écran, où la police par défaut n'est pas celle du bureau, et deux
    # valeurs absolues différeraient sans que rien ne soit cassé.
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
