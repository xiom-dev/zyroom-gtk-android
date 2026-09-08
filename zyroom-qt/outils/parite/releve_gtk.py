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


#: Les commandes qu'un panneau peut porter, et ou l'on cesse de descendre.
#:
#: Un `Gtk.DropDown` porte un bouton et neuf etiquettes, un `Gtk.SearchEntry`
#: un `Gtk.Text`, une case du groupe « Bonus » une pastille et un libelle.
#: Descendre plus bas ferait compter trois commandes la ou l'oeil en voit une.
COMMANDES = (Gtk.DropDown, Gtk.SearchEntry, Gtk.SpinButton, Gtk.CheckButton,
             Gtk.MenuButton, Gtk.Entry, Gtk.Button, Gtk.Label)


def commandes(panneau):
    """Les commandes d'un panneau, dans l'ordre ou l'oeil les rencontre."""
    if isinstance(panneau, COMMANDES):
        yield panneau
        return
    enfant = (panneau.get_first_child()
              if hasattr(panneau, "get_first_child") else None)
    while enfant is not None:
        yield from commandes(enfant)
        enfant = enfant.get_next_sibling()


def contenu_de_barre(barre) -> dict:
    """Ce qu'une barre de filtres donne a lire.

    **La reponse mecanique a « onglet par onglet, titre par titre ».** Le
    controle ne regardait qu'un ecran, l'inventaire au repos : le journal et
    les cinq ecrans de « Bonus » n'etaient mesures par personne, et leurs
    divergences se decouvraient a l'oeil, apres livraison. Chaque ecran porte
    une barre en tete, et c'est la que vivent son invite de recherche, ses
    listes deroulantes, ses boutons et ses etiquettes.

    Les libelles d'etat -- « Lecture de la meteo… », « Effectif · 177 » --
    n'en font pas partie : ils disent l'instant et les donnees, pas l'aspect.
    L'appelant les vide avant de mesurer.
    """
    lu = {"invite": None, "listes": [], "boutons": [], "etiquettes": []}
    for w in commandes(barre):
        if isinstance(w, Gtk.DropDown):
            modele = w.get_model()
            lu["listes"].append([modele.get_string(i)
                                 for i in range(modele.get_n_items())])
        elif isinstance(w, (Gtk.SearchEntry, Gtk.Entry)):
            if lu["invite"] is None:
                lu["invite"] = w.get_placeholder_text()
        elif isinstance(w, (Gtk.Button, Gtk.MenuButton)):
            lu["boutons"].append(texte(w) or "")
        elif isinstance(w, Gtk.Label):
            mot = (w.get_text() or "").strip()
            if mot:
                lu["etiquettes"].append(mot)
    return lu


def textes_du_panneau(panneau) -> list:
    """Tout ce qui se lit dans un panneau, dans l'ordre, sans les vides.

    **Une seule liste, et non une par genre de commande.** Le panneau des
    filtres pose ses quatre bonus differemment des deux cotes -- GTK met le
    libelle dans la case a cocher, Qt le pose a cote --, si bien que trier par
    genre opposerait deux listes qui decrivent pourtant le meme ecran. Ce
    qu'on compare, ce sont les mots et l'ordre ou on les rencontre.

    Les compteurs sont ecartes : leur contenu est un nombre, pas un titre, et
    il se releve a part avec ses bornes.
    """
    mots = []
    for w in commandes(panneau):
        if isinstance(w, (Gtk.DropDown, Gtk.SpinButton)):
            continue
        mot = w.get_text() if isinstance(w, Gtk.Label) else texte(w)
        mot = (mot or "").strip()
        if mot:
            mots.append(mot)
    return mots


def tourner(millisecondes: int) -> None:
    """Fait tourner la boucle GTK pendant une vraie duree.

    **Et non un nombre de tours.** `iteration(False)` rend la main aussitot
    quand rien n'attend : deux cents tours a vide ne laissent pas passer une
    seule trame, et la fenetre reste dans l'etat ou on l'a trouvee.
    """
    contexte = GLib.MainContext.default()
    fini = []
    GLib.timeout_add(millisecondes, lambda: fini.append(True) and False)
    while not fini:
        contexte.iteration(True)


def montrer_ecran(f, nom, temoin=None) -> None:
    """Amene un ecran devant, et attend qu'il soit reellement pose.

    **Une page jamais affichee n'est pas allouee** : ses widgets mesurent
    zero, et la comparaison porterait sur du vide. La pile n'alloue son
    nouvel enfant qu'a la trame suivante -- « Avant-postes » rendait encore
    la hauteur de la page precedente, « Meteo » rendait zero --, d'ou cette
    attente, qui s'arrete des que le temoin a une hauteur.
    """
    if nom == "inventaire":
        f._stack.set_visible_child_name("inventory")
    elif nom == "journal":
        f._stack.set_visible_child_name("log")
    else:
        f._stack.set_visible_child_name("plus")
        f._plus_stack.set_visible_child_name(nom)
    # **Deux attentes, et non une.** La premiere jusqu'a ce que la page
    # existe -- une page jamais affichee mesure zero. La seconde jusqu'a ce
    # que sa mise en page se soit tue : GTK alloue d'abord aux enfants leur
    # largeur minimale, puis leur donne la naturelle a la trame suivante, et
    # une mesure prise entre les deux donnait un bouton « Copier » large de
    # quarante-huit pixels quand il en fait quatre-vingt-deux a l'ecran. La
    # capture l'a dementie ; sans elle, on corrigeait Qt sur du vent.
    for _ in range(40):
        tourner(50)
        if temoin is None or temoin.get_height() > 0:
            break
    if temoin is None:
        return
    precedente = -1
    for _ in range(20):
        tourner(60)
        if temoin.get_width() == precedente:
            return
        precedente = temoin.get_width()


def air_sous(barre, champ) -> int:
    """Les pixels entre le bas du champ de la barre et ce qui suit la barre.

    **Mesure, et non declaree.** Les deux portages ne posent pas leurs marges
    au meme endroit : GTK les met autour de la barre, Qt dedans. Comparer les
    deux nombres opposait donc « huit dehors » a « huit dedans » -- deux
    ecritures du meme ecran -- pendant que l'ecart reel, celui que l'oeil voit
    entre la derniere commande et le contenu, n'etait mesure par personne.
    """
    suivant = barre.get_next_sibling()
    if suivant is None or champ is None:
        return -1
    page = barre.get_parent()
    ok1, haut = champ.compute_bounds(page)
    ok2, bas = suivant.compute_bounds(page)
    if not (ok1 and ok2):
        return -1
    return round(bas.origin.y - (haut.origin.y + haut.size.height))


def cote(widget) -> str:
    """De quel cote une cellule du journal cale son contenu."""
    if not isinstance(widget, Gtk.Label):
        return "image"
    x = widget.get_xalign()
    return "gauche" if x < 0.25 else ("droite" if x > 0.75 else "milieu")


def journal_temoin() -> list:
    """Trois mouvements fabriques, les memes des deux cotes.

    **Le journal ne se mesure ni a vide, ni sur les donnees du joueur.** Les
    deux applications tiennent leur cache dans deux dossiers separes : celui
    de GTK avait deux mille lignes la ou celui de Qt en avait zero, et aucune
    largeur de colonne n'etait comparable. Trois lignes fabriquees ici -- une
    entree, une sortie, et une la veille pour le trait de separation --
    donnent aux deux journaux exactement le meme contenu.

    Du tresor uniquement : un objet ferait demander son icone au serveur, et
    un releve ne doit rien telecharger. Midi plutot que l'instant : a une
    seconde de minuit, « la veille » et « aujourd'hui » changeraient de sens
    entre les deux releves.
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

    # Le bloc, pour sa place et sa largeur ; le bouton lui-meme pour sa
    # hauteur. La boite qui porte les trois boutons n'a pas les memes marges
    # d'un toolkit a l'autre -- cinquante-deux pixels chez GTK pour trente-huit
    # de boutons --, et comparer ces marges-la n'apprend rien : ce qu'on voit,
    # c'est le bouton.
    situer("geo.navigation", f._plus_btn.get_parent())
    mesures.pop("geo.navigation.hauteur", None)
    situer("geo.bouton", f._plus_btn)
    mesures.pop("geo.bouton.milieu", None)
    mesures.pop("geo.bouton.largeur", None)
    situer("geo.entite", f._entity_dd)
    situer("geo.inventaire", f._inv_dd)
    situer("geo.recherche", f._search)
    return mesures


#: Le texte dont on mesure la largeur, des deux cotes.
#:
#: **Le point de controle des points de controle.** Deux toolkits n'expriment
#: pas leur police pareil -- Pango rend des unites de peripherique, Qt des
#: points -- et comparer les deux nombres n'apprend rien. La largeur d'une
#: meme chaine, elle, se compare : si elle differe, tout ce qui derive du
#: texte differe avec elle, et aucune autre mesure ne veut plus rien dire.
#: C'est exactement ce qui s'est passe deux fois -- l'agrandissement du bureau
#: d'abord, le corps de base ensuite --, et deux fois on a accuse les fenetres
#: d'un ecart qui venait de la mesure.
TEXTE_TEMOIN = "Actualiser 0123456789"


#: Le corps du texte des releves, le meme des deux cotes.
#:
#: **Sans lui, le banc mentait une seconde fois.** L'echelle du bureau avait
#: ete neutralisee, mais pas le corps de base : GTK, prive de demon XSettings,
#: retombe sur son defaut « Sans 10 », tandis que Qt gardait les neuf points
#: de Fusion. Un dixieme de moins sur chaque lettre, et toutes les mesures
#: tirees du texte suivaient -- « Entite : » faisait quarante-huit pixels d'un
#: cote et quarante-trois de l'autre, la barre de navigation quatre milliemes
#: de moins, les six colonnes du journal jusqu'a sept pixels. On accusait les
#: fenetres d'un ecart qui venait de la mesure.
#:
#: Onze points, comme le banc d'images, pour que les deux outils parlent de la
#: meme fenetre.
CORPS_RELEVE = 11


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

    # --- Chaque ecran, sa barre de filtres ---------------------------------
    # Ludo : « je veux que tu fasses une comparaison detaillee TOTALE [...]
    # fenetre par fenetre, onglet par onglet, titre par titre ». Le controle
    # ne regardait qu'un seul ecran, l'inventaire au repos ; il les regarde
    # tous. Les libelles d'etat sont vides d'abord : ils disent les donnees du
    # moment -- « Effectif · 177 », « Lecture de la meteo… » --, et les deux
    # applications ne lisent pas le meme cache.
    for etat in (f._roster_status, f._op_status, f._meteo_entete,
                 f._log_status, f._skills_status):
        etat.set_text("")
    # L'ordre du tri est un reglage sauvegarde, propre a chaque portage : deux
    # fleches opposees ne diraient rien de l'aspect.
    f._order_btn.set_label("↓")
    # L'arbre des competences a ete deplie plus haut, pour mesurer ses jauges,
    # et son bouton porte donc « Tout replier ». On le replie : c'est l'etat
    # dans lequel l'ecran s'ouvre, et celui que les deux portages doivent
    # montrer du meme mot.
    f._skills_expanded = set()
    f._refresh_skills()
    for nom, champ in (("inventaire", f._search),
                       ("journal", f._log_search),
                       ("skills", f._skills_search),
                       ("roster", f._roster_recherche),
                       ("outposts", f._op_vue),
                       ("meteo", f._meteo_refresh)):
        barre = champ.get_parent()
        lu = contenu_de_barre(barre)
        points[f"{nom}.recherche.invite"] = lu["invite"]
        points[f"{nom}.listes"] = lu["listes"]
        points[f"{nom}.boutons"] = lu["boutons"]
        points[f"{nom}.etiquettes"] = lu["etiquettes"]
        montrer_ecran(f, nom, champ)
        # `compute_bounds` et non `get_height` : c'est la mesure que `situer`
        # emploie plus bas, et deux facons de mesurer le meme champ rendaient
        # deux nombres -- trente-deux et trente-quatre -- dont l'un des deux
        # aurait accuse Qt d'un ecart de trois pixels au lieu d'un.
        ok, cadre = champ.compute_bounds(champ.get_parent())
        points[f"geo.{nom}.champ.hauteur"] = (round(cadre.size.height)
                                              if ok else -1)
        points[f"geo.{nom}.air-sous-la-barre"] = air_sous(barre, champ)
        # La hauteur de la barre elle-meme, c'est-a-dire celle de sa plus
        # haute commande. Le champ ne suffit pas : sur l'effectif, ce sont les
        # deux bascules qui commandent, et elles peuvent depasser sans que la
        # mesure du champ y voie rien.
        points[f"geo.{nom}.barre.hauteur"] = barre.get_height()
        # La largeur de chaque commande de la barre, dans l'ordre. Le champ
        # de recherche prend ce qui reste : dire qu'il est quarante pixels
        # trop court n'apprend rien tant qu'on ignore laquelle de ses voisines
        # les lui a pris.
        # `compute_bounds` et non `get_width` : sur un `Gtk.Button`, celui-ci
        # rend la largeur du contenu sans le remplissage de la feuille --
        # quarante-huit pixels pour un « Copier » qui en occupe
        # quatre-vingt-deux a l'ecran. La capture d'ecran a dementi la mesure,
        # et c'est la mesure qui avait tort.
        largeurs = []
        for w in commandes(barre):
            if isinstance(w, Gtk.Label):
                continue
            ok, cadre = w.compute_bounds(barre)
            if ok and cadre.size.width > 1:
                largeurs.append(round(cadre.size.width))
        points[f"geo.{nom}.commandes.largeurs"] = largeurs

    # --- Le panneau des filtres, ouvert -------------------------------------
    # Un menu ferme ne se compare pas : c'est ouvert qu'on voit ses quatre
    # groupes, ses titres et ses trente cases.
    bouton_filtres = next(w for w in commandes(f._search.get_parent())
                          if isinstance(w, Gtk.MenuButton))
    defilant = bouton_filtres.get_popover().get_child()
    points["filtres.panneau.textes"] = textes_du_panneau(defilant)
    points["filtres.panneau.hauteur-max"] = defilant.get_max_content_height()
    reglage = f._qmin.get_adjustment()
    points["filtres.qualite.bornes"] = [int(reglage.get_lower()),
                                        int(reglage.get_upper())]
    points["filtres.qualite.pas"] = int(reglage.get_step_increment())
    points["filtres.qualite.depart"] = [int(f._qmin.get_value()),
                                        int(f._qmax.get_value())]
    points["filtres.cases"] = len(f._all_checks)

    # --- Les deux menus de la barre du haut, ouverts eux aussi -------------
    popover = f._plus_btn.get_popover()
    points["menu.bonus.libelles"] = [
        texte(w) for w in commandes(popover.get_child())
        if isinstance(w, Gtk.Button)]
    modele = None
    for w in parcourir(f):
        if isinstance(w, Gtk.MenuButton) and w.get_menu_model() is not None:
            modele = w.get_menu_model()
            break
    points["menu.principal.libelles"] = [
        modele.get_item_attribute_value(i, "label", None).get_string()
        for i in range(modele.get_n_items())] if modele is not None else []

    # --- Le journal, sur trois mouvements fabriques ------------------------
    # Les colonnes du journal se sont deja resserrees une fois sans que rien
    # ne le voie : c'est Ludo qui l'a remarque, capture a l'appui. Trois lignes
    # identiques des deux cotes suffisent a mesurer ce qu'il voyait.
    f._log_search.set_text("")
    f._log_filter.set_selected(0)
    # La page d'abord : en arrivant sur le journal, la fenetre relit le cache
    # du joueur, et les temoins poses avant seraient balayes.
    montrer_ecran(f, "journal", f._log_search)
    f._log_entries = journal_temoin()
    f._refresh_log()
    tourner(150)
    colonnes = 0
    while f._log_grid.get_child_at(colonnes, 0) is not None:
        colonnes += 1
    points["journal.colonnes"] = colonnes
    points["journal.alignements"] = [cote(f._log_grid.get_child_at(c, 0))
                                     for c in range(colonnes)]
    # La couleur du montant vit dans le balisage Pango, que le style ignore :
    # on la relit dans le balisage lui-meme.
    for quoi, rang in (("entrant", 0), ("sortant", 1)):
        montant = f._log_grid.get_child_at(2, rang)
        teinte = re.search(r'foreground="(#[0-9a-fA-F]{6})"',
                           montant.get_label() or "")
        points[f"journal.{quoi}.couleur"] = (teinte.group(1).lower()
                                             if teinte else "sans couleur")
    horodatage = f._log_grid.get_child_at(0, 0)
    points["journal.horodatage.chasse-fixe"] = (
        "monospace" in horodatage.get_css_classes())
    image = f._log_grid.get_child_at(4, 0)
    points["journal.icone.cote"] = (image.get_pixel_size()
                                    if isinstance(image, Gtk.Image) else 0)
    # Le trait entre deux journees : un pixel peint, six d'air de chaque cote,
    # treize en tout. `measure` compte deja les marges -- inutile de les
    # rajouter, on comptait le double.
    trait = f._log_grid.get_child_at(0, 2)
    points["journal.trait-de-jour.hauteur"] = (taille(trait)[1]
                                               if trait is not None else 0)
    points["journal.trait-de-jour.rangee"] = 2
    # Le contrat du zoom : la meme plage, le meme pas, le meme facteur au
    # maximum. C'est le seul reglage d'apparence qui reste, et les deux
    # applications doivent l'entendre pareil.
    from zyroom.config import Settings as _R
    # Jusqu'ou la fenetre se laisse reduire. Il y avait la, cote GTK, une
    # barre de defilement horizontale : elle permettait a la fenetre de
    # retrecir sans fin, et a deux cents pour cent on faisait glisser la
    # fenetre entiere pour lire la saison. Sans elle, chaque toolkit refuse
    # de lui-meme de descendre sous la largeur de son contenu -- et c'est
    # cette largeur-la qu'on compare.
    points["geo.fenetre.plancher"] = f.measure(
        Gtk.Orientation.HORIZONTAL, -1)[0]
    points["zoom.crans"] = list(_R.PALIERS_ZOOM)
    points["zoom.icone-normale"] = _R.ICONE_NORMALE
    points["police.corps"] = CORPS_RELEVE
    from gi.repository import Pango
    mise = Pango.Layout(f._status.get_pango_context())
    mise.set_text(TEXTE_TEMOIN)
    # Arrondi a la dizaine : deux moteurs de rendu ne tombent pas
    # d'accord au pixel sur la meme police -- cent soixante et onze
    # contre cent soixante-quatorze --, et ce point ne cherche pas
    # cette finesse-la. Ce qu'il doit voir, c'est un corps de texte
    # qui differe d'un dixieme : la, tout le reste ment.
    points["police.largeur-temoin"] = round(
        mise.get_pixel_size().width / 10) * 10
    # La hauteur d'une ligne du journal, allouee : c'est elle qui decide
    # combien de mouvements tiennent dans un ecran.
    points["geo.journal.pas-des-rangees"] = (
        f._log_grid.get_child_at(0, 0).get_height()
        + f._log_grid.get_row_spacing())
    # Ou commence la premiere ligne du journal, sous la barre : l'air declare
    # par les marges ne dit rien -- GTK le pose autour de sa grille, Qt dans
    # les marges de sa vue --, celui-ci se voit.
    ok, rect = f._log_grid.get_child_at(0, 0).compute_bounds(f._log_search)
    points["geo.journal.premiere-ligne.depart"] = (round(rect.origin.y)
                                                   if ok else -1)
    # Ou commence chaque colonne, **en pixels depuis la premiere**. Ni en
    # milliemes de la grille -- sa largeur suit son contenu, et trois lignes
    # temoins ne l'etirent pas comme deux mille --, ni en absolu : c'est
    # l'ecartement des colonnes qui se compare, celui-la meme que Ludo avait
    # vu se resserrer.
    depart = None
    for c in range(colonnes):
        ok, rect = f._log_grid.get_child_at(c, 0).compute_bounds(f._log_grid)
        if not ok:
            continue
        if depart is None:
            depart = rect.origin.x
        points[f"geo.journal.colonne{c}.depart"] = round(rect.origin.x - depart)
    # L'inventaire revient : la geometrie qui suit mesure ses selecteurs, et
    # un widget qui n'est plus a l'ecran ne se mesure pas.
    montrer_ecran(f, "inventaire", f._search)

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
    # Le meme corps des deux cotes, impose par le reglage : c'est par lui que
    # les deux portages posent leur regle `* { font-size }`, et non par la
    # police du bureau. Ludo a d'ailleurs onze points en Qt et « comme le
    # bureau » en GTK : sans cela le controle comparerait ses deux reglages.
    from zyroom.config import Settings as _Reglages
    _Reglages.font_size = property(lambda _soi: CORPS_RELEVE)
    # Et le zoom a un : c'est desormais lui qui commande la taille du texte
    # comme celle des images, et deux fenetres zoomees differemment ne se
    # comparent pas.
    _Reglages.zoom = property(lambda _soi: 1.0)
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
