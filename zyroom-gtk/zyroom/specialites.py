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

Les quatre gouttes sont les quatre jauges du jeu, et portent leurs noms : vie,
sève, endurance, concentration. Ce sont elles qui disent à quoi un objet
prépare — la concentration au forage, l'endurance au combat, la sève à la
magie.

Le module ne dessine que ça, et le fait en Cairo : un fichier PNG par couleur
aurait été quatre images à embarquer, à retailler et à recolorer le jour où le
thème bouge.
"""
from __future__ import annotations

import math

from gi.repository import Gdk, Gtk

#: (attribut d'ItemInfo, libelle, couleur), dans l'ordre des jauges du jeu.
SPECIALITES = (
    ("hp_buff",    "Vie",           "#e2696a"),   # zy_erreur, le rouge du thème
    ("sap_buff",   "Sève",          "#4caf50"),   # success_color, son vert
    ("sta_buff",   "Endurance",     "#a97fd0"),
    ("focus_buff", "Concentration", "#4a90d9"),
)

#: La goutte, en pixels : un quart d'une icone de 48, de quoi reconnaitre une
#: couleur sans manger l'objet qu'elle qualifie.
LARGEUR = 11
HAUTEUR = 14

#: La hauteur ou la colonne a le droit de descendre, sur une icone de 48.
#: Les dix derniers pixels portent la quantite — « x11 », « x425 » —, que la
#: pile ne doit pas recouvrir.
ZONE = 38


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


def indices(item) -> set:
    """Les rangs des bonus que porte l'item, dans l'ordre de `SPECIALITES`.

    C'est ce que manipule le filtre : un ensemble d'entiers se compare à un
    ensemble de cases cochées sans rien savoir des couleurs ni des noms."""
    return {rang for rang, (attribut, _libelle, _couleur) in enumerate(SPECIALITES)
            if getattr(item, attribut, 0)}


def passe_le_filtre(item, coches: set) -> bool:
    """Vrai si l'item survit au filtre des quatre bonus.

    `coches` est l'ensemble des rangs cochés. Toutes les cases cochées, le
    filtre ne trie rien — **objets sans bonus compris**, car c'est l'état de
    repos, pas une demande. Dès qu'une case tombe, ne restent que les objets
    portant l'un des bonus encore cochés."""
    if len(coches) >= len(SPECIALITES):
        return True
    return bool(indices(item) & coches)


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


def _pas(nombre: int) -> float:
    """L'écart vertical entre deux gouttes d'une pile de `nombre`.

    Bord à bord tant qu'elles tiennent dans la zone, resserrées au-delà : trois
    gouttes de quatorze pixels dépasseraient sur la quantité, quatre sur
    l'icône voisine."""
    if nombre < 2:
        return float(HAUTEUR)
    return min(float(HAUTEUR), (ZONE - HAUTEUR) / (nombre - 1))


def hauteur_pile(nombre: int) -> int:
    """La hauteur qu'occupe une pile de `nombre` gouttes."""
    if nombre < 1:
        return 0
    return int(round((nombre - 1) * _pas(nombre) + HAUTEUR))


def _dessiner(_zone, ctx, _largeur, _hauteur, couleurs: list) -> None:
    """La pile de gouttes, de haut en bas, dans l'ordre des jauges.

    **Dessinées de bas en haut** : quand elles se resserrent, c'est la pointe
    qui passe sous la goutte du dessus, jamais le ventre — le ventre porte la
    couleur, donc le sens."""
    pas = _pas(len(couleurs))
    for rang in range(len(couleurs) - 1, -1, -1):
        _goutte(ctx, 0.0, rang * pas, couleurs[rang])


def bandeau(item) -> Gtk.DrawingArea | None:
    """La pile de gouttes à poser sur l'icône, `None` s'il n'y a aucun bonus.

    À placer dans un `Gtk.Overlay`, au-dessus de l'image de l'item.

    **Toutes les gouttes**, les unes sous les autres, dans l'ordre des jauges :
    vie, sève, endurance, concentration — rouge, vert, mauve, bleu. Un objet en
    porte trois au plus ; la pile s'arrête au-dessus du bandeau de quantité.

    **En haut à gauche** : l'API écrit la qualité en bas à droite, empile les
    étoiles de classe en haut à droite, et la quantité occupe le bas.

    Un seul widget pour toute la pile, qui la place elle-même : une grille de
    coffre en compte des centaines, et trois `DrawingArea` par case s'y
    verraient."""
    lignes = bonus(item)
    if not lignes:
        return None

    couleurs = []
    for _libelle, _valeur, couleur in lignes:
        rgba = Gdk.RGBA()
        rgba.parse(couleur)           # une fois pour toutes, pas a chaque trame
        couleurs.append(rgba)

    zone = Gtk.DrawingArea()
    zone.set_content_width(LARGEUR)
    zone.set_content_height(hauteur_pile(len(couleurs)))
    zone.set_halign(Gtk.Align.START)
    zone.set_valign(Gtk.Align.START)
    # Les gouttes ne se cliquent pas. Sans cela elles avaleraient le clic droit
    # et le double-clic destines a l'icone qu'elles recouvrent.
    zone.set_can_target(False)
    zone.set_draw_func(_dessiner, couleurs)
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
