"""Les gouttes de spécialité, posées par-dessus l'icône d'un équipement.

Une armure, une arme ou un bijou craftés portent des bonus qui dépendent des
matières employées : vie, sève, endurance, focus. Le jeu les résume par une
goutte de couleur dans un coin de l'icône, et c'est ce qu'on lit en parcourant
un coffre — bien avant d'ouvrir une fiche.

L'icône, elle, arrive toute faite de `item_icon.php` : l'API ne connaît que le
nom de fiche, la couleur et la qualité, jamais l'exemplaire. Elle ne peut donc
pas savoir que *ce* jaboté-là est monté en sève, et aucun paramètre ne le lui
dirait — vérifié : `hp`, `sta`, `focus`, `hpbuff`… renvoient la même image à
l'octet près. Les bonus, eux, sont déjà lus dans l'inventaire (`models.py`,
`_parse_craft`). Il ne reste qu'à les dessiner par-dessus.

Les quatre gouttes sont les quatre jauges du jeu, et chacune sert une
spécialité : le focus est la jauge du forage, l'endurance celle du combat, la
sève celle de la magie, les points de vie celle du soin.

Le module ne dessine que ça, et le fait en Cairo : un fichier PNG par couleur
aurait été quatre images à embarquer, à retailler et à recolorer le jour où le
thème bouge.
"""
from __future__ import annotations

import math

from gi.repository import Gdk, Gtk

#: (attribut d'ItemInfo, libelle, couleur), dans l'ordre des jauges du jeu.
SPECIALITES = (
    ("hp_buff",    "Vie",    "#e2696a"),   # zy_erreur, le rouge du thème
    ("sap_buff",   "Magie",  "#4caf50"),   # success_color, son vert
    ("sta_buff",   "Combat", "#a97fd0"),
    ("focus_buff", "Forage", "#4a90d9"),
)

#: La goutte, en pixels : un quart d'une icone de 48, de quoi reconnaitre une
#: couleur sans manger l'objet qu'elle qualifie.
LARGEUR = 11
HAUTEUR = 14


def bonus(item) -> list[tuple[str, int, str]]:
    """Les spécialités portées par un item : `[(libellé, valeur, couleur), …]`.

    Liste vide pour une matière, une graine, un objet de mission : rien à
    dessiner, et l'appelant s'épargne alors un widget."""
    trouves = []
    for attribut, libelle, couleur in SPECIALITES:
        valeur = getattr(item, attribut, 0)
        if valeur:
            trouves.append((libelle, valeur, couleur))
    return trouves


def principal(item):
    """La spécialité dominante d'un item : `(libellé, valeur, couleur)` ou `None`.

    Celle qui porte le plus gros bonus. Les quatre se comptent en points sur la
    même échelle, elles se comparent donc directement ; à égalité, l'ordre des
    jauges tranche."""
    lignes = bonus(item)
    if not lignes:
        return None
    return max(lignes, key=lambda ligne: ligne[1])


def resume(item) -> str:
    """« Vie +12, Combat +5 », pour l'infobulle.

    Une couleur seule ne se lit pas : elle se reconnaît quand on la connaît
    déjà. La ligne d'infobulle est ce qui l'apprend."""
    return ", ".join(f"{libelle} +{valeur}"
                     for libelle, valeur, _couleur in bonus(item))


def _goutte(ctx, x: float, y: float, rgba: Gdk.RGBA) -> None:
    """Une goutte : pointe en haut, ventre rond en bas, posée en (x, y)."""
    rayon = min(LARGEUR, HAUTEUR) / 2.0 - 1.0
    cx = x + LARGEUR / 2.0
    cy = y + HAUTEUR - rayon - 1.0

    ctx.new_path()
    # Le ventre : les deux tiers bas du cercle, de -30 a 210 degres. Cairo
    # tourne dans le sens des aiguilles, son axe y descendant.
    ctx.arc(cx, cy, rayon, -math.pi / 6.0, math.pi + math.pi / 6.0)
    ctx.line_to(cx, y + 1.0)          # les flancs remontent vers la pointe
    ctx.close_path()

    ctx.set_source_rgb(rgba.red, rgba.green, rgba.blue)
    ctx.fill_preserve()
    # Un cerne sombre : les icones de Ryzom sont claires et chargees, une
    # pastille sans contour s'y dissout.
    ctx.set_source_rgba(0.0, 0.0, 0.0, 0.75)
    ctx.set_line_width(1.0)
    ctx.stroke()


def _dessiner(_zone, ctx, _largeur, _hauteur, couleurs: list) -> None:
    """La rangée de gouttes, côte à côte."""
    for rang, rgba in enumerate(couleurs):
        _goutte(ctx, rang * LARGEUR, 0.0, rgba)


def bandeau(item) -> Gtk.DrawingArea | None:
    """La goutte à poser sur l'icône, `None` si l'item n'a aucun bonus.

    À placer dans un `Gtk.Overlay`, au-dessus de l'image de l'item.

    **Une seule**, celle du bonus dominant, comme dans le jeu — et l'infobulle
    dit le reste. Un item peut en porter trois ; trois gouttes font trente-trois
    pixels sur quarante-huit et viennent buter dans la qualité, que l'API écrit
    juste à côté. Une tache de couleur dit la spécialité, c'est tout ce qu'on
    lui demande en parcourant un coffre.

    **En haut à gauche.** Le jeu la pose en bas, mais son icône n'y écrit rien ;
    celle de l'API porte la quantité dans ce coin — « x11 », « x425 » —, et la
    goutte la masquait. Les deux autres coins sont pris : la qualité en bas à
    droite, les étoiles de classe en haut à droite.

    Reste que l'API dessine dans ce même coin la tache verte des objets à charge
    de sève. Les deux se superposent sur les rares équipements qui cumulent une
    charge et un bonus ; la goutte passe au-dessus, et c'est elle qu'on cherche
    en parcourant un coffre."""
    dominant = principal(item)
    if dominant is None:
        return None

    rgba = Gdk.RGBA()
    rgba.parse(dominant[2])           # une fois pour toutes, pas a chaque trame

    zone = Gtk.DrawingArea()
    zone.set_content_width(LARGEUR)
    zone.set_content_height(HAUTEUR)
    zone.set_halign(Gtk.Align.START)
    zone.set_valign(Gtk.Align.START)
    # La goutte ne se clique pas. Sans cela elle avalerait le clic droit et le
    # double-clic destines a l'icone qu'elle recouvre.
    zone.set_can_target(False)
    zone.set_draw_func(_dessiner, [rgba])
    return zone


def pastille(couleur: str) -> Gtk.DrawingArea:
    """Une goutte seule, à mettre au fil du texte d'une infobulle."""
    rgba = Gdk.RGBA()
    rgba.parse(couleur)
    zone = Gtk.DrawingArea()
    zone.set_content_width(LARGEUR)
    zone.set_content_height(HAUTEUR)
    zone.set_valign(Gtk.Align.CENTER)
    zone.set_draw_func(_dessiner, [rgba])
    return zone


def bloc_infobulle(item) -> Gtk.Box | None:
    """Les spécialités de l'item pour l'infobulle : la goutte, puis sa valeur.

    La même goutte que sur l'icône, à la même taille : c'est ce qui fait le
    lien entre la tache de couleur qu'on a vue dans la grille et le bonus
    qu'elle annonce. Le jeu montre la goutte et le nombre, sans le nommer ;
    on ajoute le nom, parce qu'une infobulle a la place de l'écrire."""
    lignes = bonus(item)
    if not lignes:
        return None

    boite = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    for libelle, valeur, couleur in lignes:
        ligne = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        ligne.append(pastille(couleur))
        ligne.append(Gtk.Label(label=f"{libelle} +{valeur}", xalign=0.0))
        boite.append(ligne)
    return boite
