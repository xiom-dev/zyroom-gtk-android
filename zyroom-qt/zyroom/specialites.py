"""Les gouttes de spécialité, posées par-dessus l'icône d'un équipement.

Une armure, une arme ou un bijou craftés portent des bonus qui dépendent des
matières employées : vie, sève, endurance, focus. Le jeu les résume par une
goutte de couleur dans un coin de l'icône, et c'est ce qu'on lit en parcourant
un coffre — bien avant d'ouvrir une fiche.

L'icône, elle, arrive toute faite de `item_icon.php` : l'API ne connaît que le
nom de fiche, la couleur et la qualité, jamais l'exemplaire. Elle ne peut donc
pas savoir que *ce* jaboté-là est monté en sève. Les bonus, eux, sont déjà lus
dans l'inventaire (`models.py`, `_parse_craft`). Il ne reste qu'à les dessiner
par-dessus.

**Ce que le portage Qt change.** La version GTK pose un `Gtk.DrawingArea`
transparent par-dessus l'image, dans un `Gtk.Overlay`. Ici on peint les
gouttes **dans** l'image elle-même, une fois, au moment où l'icône arrive :
une case de grille redevient un seul objet au lieu de trois widgets
superposés, et une grille de coffre en compte quatre cents. Le dessin, lui,
est le même — mêmes tailles, même goutte, même cerne.

La logique (quels bonus, quel filtre) est identique à celle de la version GTK,
mais ce fichier ne peut pas être partagé avec elle : sa moitié basse dessine,
et le dessin ne se partage pas entre Cairo et QPainter.
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap

#: (attribut d'ItemInfo, libelle, couleur), dans l'ordre des jauges du jeu.
SPECIALITES = (
    ("hp_buff",    "Vie",           "#e2696a"),   # zy_erreur, le rouge du theme
    ("sap_buff",   "Sève",          "#4caf50"),   # success_color, son vert
    ("sta_buff",   "Endurance",     "#a97fd0"),
    ("focus_buff", "Concentration", "#4a90d9"),
)

#: La goutte, en pixels : un quart d'une icone de 48, de quoi reconnaitre une
#: couleur sans manger l'objet qu'elle qualifie.
LARGEUR = 11
HAUTEUR = 14

#: La hauteur ou la colonne a le droit de descendre, sur une icone de 48.
#: Les dix derniers pixels portent la quantite -- "x11", "x425" --, que la
#: pile ne doit pas recouvrir.
ZONE = 38


def bonus(item) -> list[tuple[str, int, str]]:
    """Les spécialités portées par un item : `[(libellé, valeur, couleur), …]`."""
    out = []
    for attribut, libelle, couleur in SPECIALITES:
        valeur = getattr(item, attribut, 0)
        if valeur:
            out.append((libelle, valeur, couleur))
    return out


def indices(item) -> set:
    """Les rangs des spécialités portées, pour le filtre."""
    return {rang for rang, (attribut, _l, _c) in enumerate(SPECIALITES)
            if getattr(item, attribut, 0)}


def passe_le_filtre(item, coches: set) -> bool:
    """Vrai si l'item survit au filtre des quatre bonus.

    `coches` est l'ensemble des rangs cochés. Toutes les cases cochées, le
    filtre ne trie rien — **objets sans bonus compris**, car c'est l'état de
    repos, pas une demande. Dès qu'une case tombe, ne restent que les objets
    portant l'un des bonus encore cochés.
    """
    if len(coches) >= len(SPECIALITES):
        return True
    return bool(indices(item) & coches)


def resume(item) -> str:
    """« Vie +12, Sève +5 », pour l'infobulle.

    Une couleur seule ne se lit pas : elle se reconnaît quand on la connaît
    déjà. La ligne d'infobulle est ce qui l'apprend.
    """
    return ", ".join(f"{libelle} +{valeur}"
                     for libelle, valeur, _couleur in bonus(item))


def _pas(nombre: int) -> float:
    """L'écart vertical entre deux gouttes d'une pile de `nombre`.

    Bord à bord tant qu'elles tiennent dans la zone, resserrées au-delà : trois
    gouttes de quatorze pixels dépasseraient sur la quantité, quatre sur
    l'icône voisine.
    """
    if nombre < 2:
        return float(HAUTEUR)
    return min(float(HAUTEUR), (ZONE - HAUTEUR) / (nombre - 1))


def hauteur_pile(nombre: int) -> int:
    """La hauteur qu'occupe une pile de `nombre` gouttes."""
    if nombre < 1:
        return 0
    return int(round((nombre - 1) * _pas(nombre) + HAUTEUR))


def _goutte(peintre: QPainter, x: float, y: float, couleur: QColor) -> None:
    """Une goutte : pointe en haut, ventre rond en bas, posée en (x, y)."""
    rayon = min(LARGEUR, HAUTEUR) / 2.0 - 1.0
    cx = x + LARGEUR / 2.0
    cy = y + HAUTEUR - rayon - 1.0

    # Le ventre : les deux tiers bas du cercle. Cairo balayait de -30 a 210
    # degres dans le sens horaire ; Qt compte ses angles a l'envers, d'ou le
    # depart a +30 et un balayage negatif de 240 degres -- meme arc a l'ecran.
    boite = QRectF(cx - rayon, cy - rayon, rayon * 2.0, rayon * 2.0)
    chemin = QPainterPath()
    chemin.arcMoveTo(boite, 30.0)
    chemin.arcTo(boite, 30.0, -240.0)
    chemin.lineTo(cx, y + 1.0)        # les flancs remontent vers la pointe
    chemin.closeSubpath()

    peintre.setBrush(couleur)
    # Un cerne sombre : les icones de Ryzom sont claires et chargees, une
    # pastille sans contour s'y dissout.
    peintre.setPen(QPen(QColor(0, 0, 0, 191), 1.0))
    peintre.drawPath(chemin)


def _peindre_pile(peintre: QPainter, couleurs: list, x: float = 0.0,
                  y: float = 0.0) -> None:
    """La pile de gouttes, de haut en bas, dans l'ordre des jauges.

    **Dessinées de bas en haut** : quand elles se resserrent, c'est la pointe
    qui passe sous la goutte du dessus, jamais le ventre — le ventre porte la
    couleur, donc le sens.
    """
    pas = _pas(len(couleurs))
    for rang in range(len(couleurs) - 1, -1, -1):
        _goutte(peintre, x, y + rang * pas, couleurs[rang])


def appliquer(image: QPixmap, item) -> QPixmap:
    """L'icône avec sa pile de gouttes peinte dessus, en haut à gauche.

    Rend l'image telle quelle si l'objet ne porte aucun bonus.

    **En haut à gauche** : l'API écrit la qualité en bas à droite, empile les
    étoiles de classe en haut à droite, et la quantité occupe le bas.
    """
    lignes = bonus(item)
    if not lignes or image.isNull():
        return image

    couleurs = [QColor(couleur) for _libelle, _valeur, couleur in lignes]
    # Une copie : le QPixmap d'origine peut etre partage entre plusieurs cases
    # de la grille (le meme objet y figure souvent plusieurs fois), et le
    # peindre en place les tacherait toutes.
    sortie = QPixmap(image)
    peintre = QPainter(sortie)
    peintre.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    _peindre_pile(peintre, couleurs)
    peintre.end()
    return sortie


def pastille(couleur: str) -> QPixmap:
    """Une goutte seule, à poser au fil du texte d'une infobulle."""
    image = QPixmap(LARGEUR, HAUTEUR)
    image.fill(Qt.GlobalColor.transparent)
    peintre = QPainter(image)
    peintre.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    _goutte(peintre, 0.0, 0.0, QColor(couleur))
    peintre.end()
    return image


#: Les pastilles deja encodees, une par couleur : une infobulle se construit
#: au survol, et redessiner quatre gouttes a chaque passage de souris serait
#: du gaspillage.
_PASTILLES_HTML: dict = {}


def pastille_html(couleur: str) -> str:
    """La goutte, encodée en PNG dans une balise `<img>`.

    Qt sait lire du texte enrichi dans une infobulle, mais il ne sait y mettre
    d'image que par une adresse — et une image en mémoire n'en a pas. Une
    adresse `data:` en tient lieu : l'image voyage dans le texte lui-même.
    C'est ce qui permet de garder, dans l'infobulle, la goutte exacte qu'on
    voit sur l'icône — et non son nom, qu'il faudrait traduire de tête.
    """
    if couleur in _PASTILLES_HTML:
        return _PASTILLES_HTML[couleur]
    from PySide6.QtCore import QBuffer, QByteArray
    octets = QByteArray()
    tampon = QBuffer(octets)
    tampon.open(QBuffer.OpenModeFlag.WriteOnly)
    pastille(couleur).save(tampon, "PNG")
    tampon.close()
    encode = bytes(octets.toBase64().data()).decode("ascii")
    _PASTILLES_HTML[couleur] = f'<img src="data:image/png;base64,{encode}">'
    return _PASTILLES_HTML[couleur]


def bloc_infobulle_html(item) -> str:
    """Les spécialités de l'objet pour l'infobulle : la goutte, puis sa valeur.

    La même goutte que sur l'icône, à la même taille : c'est ce qui fait le
    lien entre la tache de couleur vue dans la grille et le bonus qu'elle
    annonce. Le jeu montre la goutte et le nombre, sans le nommer ; on ajoute
    le nom, parce qu'une infobulle a la place de l'écrire.
    """
    lignes = bonus(item)
    if not lignes:
        return ""
    return "<br>".join(
        f"{pastille_html(couleur)}&nbsp;{libelle} +{valeur}"
        for libelle, valeur, couleur in lignes)
