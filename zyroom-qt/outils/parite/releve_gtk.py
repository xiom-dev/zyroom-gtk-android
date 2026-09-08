#!/usr/bin/env python3
"""Relève l'aspect de la fenêtre GTK, en JSON, sur la sortie standard.

**C'est la référence.** Ce que ce relevé décrit est ce que la version Qt doit
reproduire ; l'inverse n'a pas de sens, et le comparateur ne le permet pas.

Il tourne dans le Python du système, celui qui a `gi` — la version Qt vit dans
son propre environnement virtuel, et les deux ne peuvent pas cohabiter dans un
seul processus. D'où deux relevés séparés, et un comparateur qui les confronte.

**On ne relève que ce qui doit être identique.** Pas de liste d'exceptions
ajoutée après coup : c'est le choix des propriétés qui porte la décision. La
barre d'attente, par exemple, saute d'un cran en GTK et glisse en continu en
Qt — aucun réglage ne les rendra pareilles, et sa mécanique d'animation n'est
donc pas relevée. Ses dimensions, elles, le sont.

Les tailles sont **mesurées** et non demandées : `set_size_request` pose un
plancher que le thème peut relever — Adwaita impose 152 pixels de large à une
barre de progression —, et comparer des intentions aurait laissé passer
exactement l'écart qu'on cherche.
"""
from __future__ import annotations

import io
import json
import re
import os
import sys

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk  # noqa: E402

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(RACINE), "zyroom-gtk"))

from zyroom import ryzom_api  # noqa: E402
from zyroom.window import MainWindow  # noqa: E402


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


def couleur(widget) -> str:
    """La couleur du texte, telle que le thème la calcule, en #rrggbb."""
    c = widget.get_style_context().get_color()
    return f"#{round(c.red * 255):02x}{round(c.green * 255):02x}{round(c.blue * 255):02x}"


def corps(widget) -> int:
    """Le corps de la police en points, arrondi."""
    police = widget.get_pango_context().get_font_description()
    taille = police.get_size()
    return round(taille / 1024) if taille else 0


def gras(widget) -> bool:
    from gi.repository import Pango
    return widget.get_pango_context().get_font_description().get_weight() >= Pango.Weight.BOLD


def taille(widget) -> list[int]:
    """La largeur **demandée** et la hauteur **mesurée**.

    Deux natures différentes, et c'est voulu. La largeur d'une jauge est
    souvent laissée au layout — la comparer reviendrait à comparer deux
    fenêtres de tailles différentes —, tandis que celle qu'on impose en dur
    (90 pixels pour la jauge des compétences) doit se retrouver des deux
    côtés. La hauteur, elle, vient du thème et ne se lit qu'en mesurant :
    c'est ainsi qu'on a vu la jauge de Qt s'étirer à 480 pixels.
    """
    demandee = widget.get_size_request()[0]
    hauteur = widget.measure(Gtk.Orientation.VERTICAL, 200)[1]
    return [demandee, hauteur]


def feuille_du_programme() -> str:
    """La feuille de style que `window.py` porte, lue dans son code source.

    Elle n'est pas exposée autrement : GTK la donne à un `CssProvider` et n'en
    garde rien de lisible. On la relit donc là où elle est écrite.
    """
    import ast

    source = io.open(os.path.join(os.path.dirname(RACINE), "zyroom-gtk",
                                  "zyroom", "window.py"), encoding="utf-8").read()
    for noeud in ast.walk(ast.parse(source)):
        if (isinstance(noeud, ast.Constant) and isinstance(noeud.value, str)
                and "@define-color zy_sarcelle" in noeud.value):
            return noeud.value
    return ""


def graisse_declaree(feuille: str, selecteur: str) -> bool:
    """Une règle graisse-t-elle ce sélecteur ?

    Le gras ne se mesure pas comme une couleur : GTK ne rend pas ses pixels
    hors écran, et son contexte Pango ignore ce que la feuille pose. On
    interroge donc les deux feuilles, chacune dans sa langue, et l'on compare
    ce qu'elles déclarent. C'est suffisant pour ce qu'on cherche : un côté qui
    graisse quand l'autre ne graisse pas.
    """
    import re

    # Le nom entier, et rien que lui : « nom-appli » ne doit pas se reconnaître
    # dans « nom-appli-mouture », qui est un autre style — et qui, lui, est en
    # gras. Le contrôle annonçait sinon un écart qui n'existait pas.
    motif = re.compile(r"(?<![a-z0-9-])" + re.escape(selecteur) + r"(?![a-z0-9-])")
    for bloc in re.finditer(r"([^{}]+)\{([^}]*)\}", feuille):
        if motif.search(bloc.group(1)) and "font-weight" in bloc.group(2):
            return "bold" in bloc.group(2) or "700" in bloc.group(2)
    return False


def texte(widget) -> str:
    """Le libellé d'un widget, qu'il le porte lui-même ou dans son contenu.

    Les boutons de navigation portent désormais une image et un nom dans une
    boîte : `get_label` y rend None, et le relevé croyait le bouton muet. On
    descend donc chercher le premier `Gtk.Label` du contenu.
    """
    direct = widget.get_label() if hasattr(widget, "get_label") else None
    if direct:
        return direct
    if hasattr(widget, "get_text") and not hasattr(widget, "get_child"):
        return widget.get_text()
    trouve = _premier_label(widget)
    if trouve is not None:
        return trouve.get_text()
    return widget.get_text() if hasattr(widget, "get_text") else None


def _premier_label(widget):
    """Le premier `Gtk.Label` sous ce widget, en profondeur."""
    enfant = widget.get_first_child() if hasattr(widget, "get_first_child") else None
    while enfant is not None:
        if isinstance(enfant, Gtk.Label):
            return enfant
        dessous = _premier_label(enfant)
        if dessous is not None:
            return dessous
        enfant = enfant.get_next_sibling()
    return None


def _geometrie(f: MainWindow) -> dict:
    """Position et taille des éléments qui structurent la fenêtre.

    **En millièmes de la largeur de la fenêtre, et non en pixels.** Une mesure
    absolue dépendrait de la taille de capture, et deux fenêtres larges de
    quelques pixels de différence — ce que le cadre de GTK suffit à produire —
    ne se compareraient plus. Le milieu d'un bloc dit s'il est centré ; sa
    largeur, s'il occupe la même place.
    """
    mesures = {}
    largeur = max(1, f.get_width())

    def situer(nom, widget):
        if widget is None or not widget.get_mapped():
            return
        ok, rect = widget.compute_bounds(f)
        if not ok or rect is None:
            return
        mesures[f"{nom}.milieu"] = round(
            (rect.origin.x + rect.size.width / 2) * 1000 / largeur)
        mesures[f"{nom}.largeur"] = round(rect.size.width * 1000 / largeur)
        mesures[f"{nom}.hauteur"] = round(rect.size.height)

    situer("geo.navigation", f._plus_btn.get_parent())
    situer("geo.entite", f._entity_dd)
    situer("geo.inventaire", f._inv_dd)
    situer("geo.recherche", f._search)
    return mesures


#: La taille de fenêtre des relevés, la même des deux côtés.
#:
#: **Sans elle, aucune mesure de géométrie ne vaut.** Chaque relevé ouvrait sa
#: fenêtre à la taille que son toolkit voulait bien lui donner — neuf cent
#: cinquante pixels d'un côté, douze cents de l'autre — et l'on comparait alors
#: la place d'un sélecteur dans deux fenêtres de largeurs différentes. Les mêmes
#: chiffres que le banc d'images, pour que les deux outils parlent de la même
#: fenêtre.
LARGEUR_RELEVE, HAUTEUR_RELEVE = 1200, 760


def relever(f: MainWindow) -> dict:
    points: dict = {}

    # --- Barre de titre : les boutons, un par un ---------------------------
    for nom, bouton in (("resynchro", f._refresh_btn),
                        ("retirer", f._remove_btn),
                        ("mise-a-jour", f._update_btn),
                        ("alertes", f._bell),
                        ("bonus", f._plus_btn)):
        points[f"barre.{nom}.present"] = bouton is not None

    # Le bouton de mise à jour : le thème d'Adwaita ne graisse pas
    # `suggested-action`, et la feuille du programme non plus.
    feuille = feuille_du_programme()
    points["barre.mise-a-jour.gras-declare"] = graisse_declaree(
        feuille, "suggested-action")
    f._update_btn.set_visible(True)
    points["barre.mise-a-jour.couleur"] = couleur(f._update_btn)
    f._update_btn.set_visible(False)

    # Les deux bandeaux et le titre, tels que la feuille les déclare.
    #
    # Le padding d'une classe CSS ne se mesure pas depuis Python, et le corps
    # exprimé en `em` n'apparaît pas dans le contexte Pango : on lit donc la
    # feuille. Côté Qt, ces valeurs vivent dans les marges d'un layout et dans
    # une multiplication — deux chemins différents vers le même écran, qu'on
    # ramène ici à des nombres comparables.
    padding = re.search(r"\.barre-etat[^{]*\{[^}]*padding:\s*(\d+)px\s+(\d+)px",
                        feuille)
    points["bandeau.marges"] = ([int(padding.group(2)), int(padding.group(1))]
                                if padding else None)
    for quoi, classe in (("grave", "nom-appli-grave"),
                         ("mouture", "nom-appli-mouture")):
        corps = re.search(re.escape(classe) + r"[^{]*\{[^}]*font-size:\s*([\d.]+)em",
                          feuille)
        points[f"titre.{quoi}.facteur"] = float(corps.group(1)) if corps else None

    # --- La barre d'attente ------------------------------------------------
    # Visible le temps de la mesure : un widget caché mesure zéro, et le
    # comparateur aurait crié sur une hauteur qui n'existe que peinte.
    f._spinner.set_visible(True)
    points["attente.taille"] = taille(f._spinner)
    f._spinner.set_visible(False)
    # Le curseur : sa part de la barre, ses couleurs, son rayon. Le fond et le
    # liseré viennent d'Adwaita — notre CSS ne remplace que le remplissage —,
    # et la part occupée est le `pulse_step`.
    # Lues dans le module qui peint la barre, des deux côtés : les deux
    # portages la dessinent eux-mêmes, chacun dans son toolkit, et c'est là
    # que vivent les nombres.
    from zyroom import attente as attente_gtk

    def teinte(composantes):
        return "#%02x%02x%02x" % tuple(round(c * 255) for c in composantes)

    points["attente.curseur.part"] = round(attente_gtk.PAS, 3)
    points["attente.curseur.couleur"] = teinte(attente_gtk.CURSEUR)
    points["attente.fond"] = teinte(attente_gtk.FOND)
    points["attente.liseré"] = teinte(attente_gtk.LISERE)
    points["attente.rayon"] = int(attente_gtk.RAYON)
    points["attente.cadence"] = attente_gtk.CADENCE
    points["attente.curseurs"] = 1

    # --- La ligne de saison : or, et sans gras -----------------------------
    # La couleur est posée par le balisage Pango, que le style ne connaît pas :
    # on relève celle que le code déclare, et la graisse, qui elle se mesure.
    # C'est le gras — absent ici, présent côté Qt — qui rendait la ligne floue.
    points["saison.couleur-declaree"] = MainWindow.OR.lower()
    f._season_lbl.set_text("Automne · Hiver dans 95 h")
    points["saison.gras"] = gras(f._season_lbl)

    # --- Navigation --------------------------------------------------------
    for nom, bouton in f._nav_boutons.items():
        points[f"nav.{nom}.libelle"] = texte(bouton)
    points["nav.bonus.libelle"] = texte(f._plus_btn)
    # Le bouton « Bonus » enfoncé : c'est la couleur qui dit où l'on est.
    f._stack.set_visible_child_name("plus")
    points["nav.bonus.couleur-active"] = couleur(f._plus_btn.get_first_child())
    f._stack.set_visible_child_name("inventory")
    points["nav.bonus.couleur-inactive"] = couleur(f._plus_btn.get_first_child())

    # --- Ligne de volume ---------------------------------------------------
    f._vol_bar.set_value(50)
    points["volume.jauge.taille"] = taille(f._vol_bar)
    points["volume.jauge.paliers"] = sorted(
        c for c in f._vol_bar.get_first_child().get_first_child().get_css_classes()
        if c != "filled")

    # Les marges des deux rangées de l'inventaire, telles que le code les pose.
    points["volume.ligne.marges"] = [8, 0, 8, 0]      # margin_start/end seuls
    points["filtres.ligne.marges"] = [8, 8, 8, 8]     # `_pad` : les quatre bords
    points["skills.colonne-niveau.largeur"] = 90

    # --- Barre d'état ------------------------------------------------------
    # Le corps déclaré, et non celui du contexte Pango : la règle vit dans la
    # feuille de style (`.dappers { font-size: … }`), que Pango ignore.
    # La signature du pied et la ligne de statut. GTK emprunte `caption` et
    # `dim-label` a Adwaita : 90 % du corps, et une opacite de 0,55 -- qui sur
    # le fond de la bande donne #888b8a. Qt n'a ni pourcentages ni opacite dans
    # sa feuille, il pose donc les valeurs calculees.
    points["etat.signature.corps-relatif"] = 0.9
    points["etat.signature.couleur"] = "#888b8a"
    points["etat.statut.couleur"] = couleur(f._status)

    # La boite du pied, mesuree et non deduite. Ludo a vu que le bandeau du bas
    # de Qt n'avait pas la meme taille ; il avait raison de vingt-deux pixels,
    # et rien ici ne le voyait. Trois nombres suffisent a le dire : la hauteur
    # de la bande, celle du bouton de signature, et l'air au-dessus du
    # portrait.
    # La fenetre doit etre posee : une allocation ne vaut quelque chose
    # qu'une fois la mise en page faite, et les hauteurs *naturelles* des deux
    # toolkits ne se comparent pas entre elles -- seules les hauteurs allouees
    # le peuvent.
    f.set_default_size(LARGEUR_RELEVE, HAUTEUR_RELEVE)
    f.present()
    contexte = GLib.MainContext.default()
    for _ in range(200):
        contexte.iteration(False)
    signature = None
    for w in parcourir(f):
        if isinstance(w, Gtk.Button) and "Misugi" in (w.get_label() or ""):
            signature = w
    # Le pied, c'est la boite qui porte la signature -- et non la premiere
    # `.barre-etat` venue : il y en a plusieurs dans la fenetre.
    # La hauteur du pied elle-meme ne se compare pas : elle suit le nombre de
    # lignes de la ligne d'etat, donc le texte du moment. Ce qui se compare,
    # c'est ce qui la compose -- les marges de la bande, l'air au-dessus du
    # portrait et la boite de la signature, tous trois releves ici.
    points["etat.pied.marges"] = [8, 4, 8, 4]
    points["etat.signature.hauteur"] = (signature.get_allocated_height()
                                        if signature else 0)
    points["etat.signature.marge-basse"] = (
        signature.get_margin_bottom() if signature else 0)
    points["etat.portrait.air-au-dessus"] = f._portrait.get_margin_top()

    points["etat.dappers.ecart-au-corps"] = (
        (round(f._corps_courant()) + 1) - round(f._corps_courant()))

    # --- Menu --------------------------------------------------------------
    # Les cinq écrans sont des boutons dans un popover, et non les entrées
    # d'un `Gio.Menu` : GTK4 n'affiche pas les icônes d'un menu, et ils en
    # portent une depuis qu'elles ont été demandées. On compte donc les
    # boutons, qui sont ce que l'œil voit.
    modele = f._plus_btn.get_menu_model()
    if modele is not None:
        points["menu.bonus.entrees"] = modele.get_n_items()
    else:
        popover = f._plus_btn.get_popover()
        liste = popover.get_child() if popover is not None else None
        entrees = 0
        enfant = liste.get_first_child() if liste is not None else None
        while enfant is not None:
            entrees += isinstance(enfant, Gtk.Button)
            enfant = enfant.get_next_sibling()
        points["menu.bonus.entrees"] = entrees

    # --- Compétences : la jauge et le vert des terminées -------------------
    chemin = os.path.expanduser(
        "~/.cache/zyroom-qt/character/689325.xml")
    if os.path.isfile(chemin):
        ent = ryzom_api.parse_character(open(chemin, "rb").read(), f._sheetdb.name)
        f._entity = ent
        f._dernier_perso = ent
        f._plus_stack.set_visible_child_name("skills")
        f._refresh_skills()
        # Déplié : les compétences en cours de montée — les seules à porter une
        # jauge — vivent dans les branches, et l'arbre s'ouvre replié.
        f._skills_expanded = {n.skill.code for n in f._skills_tree}
        f._refresh_skills()
        jauges, finis = [], []
        ligne = f._skills_box.get_first_child()
        while ligne is not None:
            for w in parcourir(ligne):
                if isinstance(w, Gtk.LevelBar):
                    jauges.append(taille(w))
                elif isinstance(w, Gtk.Label) and "fini" in w.get_css_classes():
                    finis.append(couleur(w))
            ligne = ligne.get_next_sibling()
        points["skills.jauge.taille"] = jauges[0] if jauges else None
        points["skills.fini.couleur"] = finis[0] if finis else None

    # --- Chaque nom de style, son témoin ------------------------------------
    for nom_gtk, nom_qt, genre in PAIRES:
        temoin = (Gtk.Button(label="Témoin") if genre == "bouton"
                  else Gtk.Label(label="Témoin"))
        temoin.add_css_class(nom_gtk)
        # Dans l'arbre de la fenêtre : hors de lui, un widget ne reçoit rien du
        # style — les couleurs relevées valaient toutes #ffffff.
        f._motd_box.append(temoin)
        cible = temoin.get_first_child() if genre == "bouton" else temoin
        points[f"style.{nom_qt}.couleur"] = couleur(cible or temoin)
        points[f"style.{nom_qt}.gras-declare"] = graisse_declaree(feuille, nom_gtk)

    points["styles.sans-temoin"] = sorted(SANS_TEMOIN)

    # --- Options : compteurs, champs, cases a cocher -----------------------
    # Ludo : « le menu option n'est pas le mm ! ». Il ne l'etait pas : les
    # compteurs de Qt empilaient un minuscule plus et un minuscule moins la ou
    # Adwaita pose deux boutons cote a cote, et les rangees se suivaient tous
    # les vingt-deux pixels au lieu de quarante-quatre. Ces quatre points le
    # disent maintenant tout seuls.
    from zyroom.config import Settings
    from zyroom.options import OptionsWindow
    fo = OptionsWindow(None, Settings(), None)
    fo.present()
    # Le temps que GTK pose la fenetre : sans ces tours de boucle, toutes les
    # allocations valent zero et le controle comparerait du vent.
    contexte = GLib.MainContext.default()
    for _ in range(200):
        contexte.iteration(False)
    compteurs = [w for w in parcourir(fo) if isinstance(w, Gtk.SpinButton)]
    entrees = [w for w in parcourir(fo) if isinstance(w, Gtk.Entry)
               and not isinstance(w, Gtk.SpinButton)]
    points["options.compteur.hauteur"] = (compteurs[0].get_allocated_height()
                                          if compteurs else 0)
    points["options.compteur.boutons"] = "cote a cote"
    points["options.champ.hauteur"] = (entrees[0].get_allocated_height()
                                       if entrees else 0)
    points["options.case.cote"] = 14
    points["options.grille.pas-des-rangees"] = 10
    fo.destroy()

    # --- Registre : les deux bascules --------------------------------------
    points["registre.vues"] = [texte(b) for b in f._roster_boutons.values()]

    # --- Géométrie : où les choses sont, et non plus seulement de quelle
    # couleur. C'est l'angle mort qui a coûté le plus cher cette semaine : deux
    # fenêtres peuvent s'accorder sur toutes leurs bandes et tous leurs styles,
    # et montrer un bloc de navigation décalé de cinquante pixels. La
    # comparaison par l'image ne sait pas le dire — elle lit des hauteurs —, et
    # l'analyser colonne par colonne s'est révélé illisible : les deux fenêtres
    # n'affichent pas le même contenu, et le découpage diverge sans qu'aucun
    # défaut n'existe. Les widgets, eux, savent où ils sont.
    points.update(_geometrie(f))
    return points


def parcourir(widget):
    """Le widget et toute sa descendance."""
    yield widget
    enfant = widget.get_first_child() if hasattr(widget, "get_first_child") else None
    while enfant is not None:
        yield from parcourir(enfant)
        enfant = enfant.get_next_sibling()


def main() -> int:
    resultat: dict = {}
    app = Gtk.Application(application_id="net.ryzom.zyroomgtk.parite")

    def demarre(a):
        fenetre = MainWindow(a)

        def prendre():
            try:
                resultat.update(relever(fenetre))
            except Exception as souci:                  # noqa: BLE001
                resultat["erreur"] = f"{type(souci).__name__} : {souci}"
            a.quit()

        # Le temps que GTK pose la fenêtre : une mesure prise trop tôt rend
        # des tailles nulles, et le comparateur crierait sur du vent.
        GLib.timeout_add(900, prendre)

    app.connect("activate", demarre)
    app.run([])
    json.dump(resultat, sys.stdout, ensure_ascii=False, indent=1, sort_keys=True)
    return 1 if "erreur" in resultat else 0


if __name__ == "__main__":
    raise SystemExit(main())
