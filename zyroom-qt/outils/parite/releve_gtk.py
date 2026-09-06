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

import json
import os
import sys

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk  # noqa: E402

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(RACINE), "zyroom-gtk"))

from zyroom import ryzom_api  # noqa: E402
from zyroom.window import MainWindow  # noqa: E402


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


def texte(widget) -> str:
    return widget.get_label() if hasattr(widget, "get_label") else widget.get_text()


def relever(f: MainWindow) -> dict:
    points: dict = {}

    # --- Barre de titre : les boutons, un par un ---------------------------
    for nom, bouton in (("resynchro", f._refresh_btn),
                        ("retirer", f._remove_btn),
                        ("mise-a-jour", f._update_btn),
                        ("alertes", f._bell),
                        ("bonus", f._plus_btn)):
        points[f"barre.{nom}.present"] = bouton is not None

    # --- La barre d'attente ------------------------------------------------
    # Visible le temps de la mesure : un widget caché mesure zéro, et le
    # comparateur aurait crié sur une hauteur qui n'existe que peinte.
    f._spinner.set_visible(True)
    points["attente.taille"] = taille(f._spinner)
    f._spinner.set_visible(False)

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

    # --- Barre d'état ------------------------------------------------------
    # Le corps déclaré, et non celui du contexte Pango : la règle vit dans la
    # feuille de style (`.dappers { font-size: … }`), que Pango ignore.
    points["etat.dappers.ecart-au-corps"] = (
        (round(f._corps_courant()) + 1) - round(f._corps_courant()))

    # --- Menu --------------------------------------------------------------
    modele = f._plus_btn.get_menu_model()
    points["menu.bonus.entrees"] = modele.get_n_items() if modele else 0

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

    # --- Registre : les deux bascules --------------------------------------
    points["registre.vues"] = [texte(b) for b in f._roster_boutons.values()]
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
