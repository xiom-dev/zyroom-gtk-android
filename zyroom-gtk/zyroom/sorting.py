"""Regroupement des objets pour l'affichage.

`ItemType` reproduit fidèlement les sept catégories du zyRoom d'origine, ce qui
convient au calcul des volumes mais pas au classement : dans un coffre de
guilde, la moitié des objets y tombent dans « autre » et se retrouvent donc
dispersés — recharges de sève, feux d'artifice, potions et objets de métier
mêlés.

Ce module définit un classement plus fin, à seule fin de tri et d'affichage. Il
n'entre pas dans les calculs et ne modifie pas les objets.

Les matières premières sont regroupées par matériau puis présentées du plus bas
niveau au plus haut, ce qui met en évidence ce qu'on possède d'une même matière.
"""

from __future__ import annotations

import re
from enum import IntEnum

from .models import ItemInfo, ItemType


class Family(IntEnum):
    """Familles d'objets, dans l'ordre où elles sont présentées.

    Les matières premières viennent en tête : c'est l'essentiel du contenu d'un
    coffre de guilde. Suivent les objets fabriqués, puis les consommables, puis
    ce qui ne se range nulle part.
    """

    RAW_HARVESTED = 0      # matières forées
    RAW_LOOTED = 1         # matières issues de créatures
    RAW_SYSTEM = 2         # matières spéciales
    EQUIPMENT = 3          # armes, armures, bijoux
    TOOL = 4               # outils d'artisanat
    CATALYST = 5           # catalyseurs d'expérience
    SAP_RECHARGE = 6       # recharges de sève
    POTION = 7             # potions et améliorations
    FIREWORK = 8           # feux d'artifice
    TELEPORT = 9           # cristaux de téléportation
    JOB_ITEM = 10          # objets de mission et de métier
    COMPONENT = 11         # composants et pièces
    EVENT = 12             # objets d'événement
    OTHER = 13             # le reste

    @property
    def label(self) -> str:
        return _LABELS[self]


_LABELS = {
    Family.RAW_HARVESTED: "Matières forées",
    Family.RAW_LOOTED: "Matières de créature",
    Family.RAW_SYSTEM: "Matières spéciales",
    Family.EQUIPMENT: "Équipement",
    Family.TOOL: "Outils",
    Family.CATALYST: "Catalyseurs",
    Family.SAP_RECHARGE: "Recharges de sève",
    Family.POTION: "Potions",
    Family.FIREWORK: "Feux d'artifice",
    Family.TELEPORT: "Téléportation",
    Family.JOB_ITEM: "Objets de métier",
    Family.COMPONENT: "Composants",
    Family.EVENT: "Événements",
    Family.OTHER: "Divers",
}

# Reconnaissance par nom de fiche. L'ordre compte : le premier motif qui
# correspond l'emporte.
_PATTERNS: tuple[tuple[re.Pattern, Family], ...] = (
    (re.compile(r"^item_sap_recharge"), Family.SAP_RECHARGE),
    (re.compile(r"^conso_fireworks"), Family.FIREWORK),
    (re.compile(r"^(pvp_boost|ipoc|ipk)_?"), Family.POTION),
    (re.compile(r"^rpjobitem"), Family.JOB_ITEM),
    (re.compile(r"^compo_"), Family.COMPONENT),
    (re.compile(r"^event_"), Family.EVENT),
    (re.compile(r"^tp_ka"), Family.TELEPORT),
)

# Matière première : « m0497dxape01.sitem ». Les quatre chiffres identifient la
# matière, indépendamment de sa qualité et de son écosystème.
_RAW_MATERIAL = re.compile(r"^m0?(\d{3,4})")

# Pièces d'une tenue et bijoux d'une parure. Une fiche d'armure se lit « ic » +
# peuple + « a » + poids + pièce + qualité de fabrication : « icmahb_3 » est la
# botte (b) d'une tenue lourde (h) matis. Un bijou suit la même règle avec
# « j » : « iczja » est l'anneau de cheville zoraï. Retirer la lettre de pièce
# donne donc la tenue elle-même.
_ARMOUR = re.compile(r"^(ic[a-z]a[a-z])([a-z])(_\d+)?\.sitem$")
_JEWEL = re.compile(r"^(ic[a-z]j)([a-z])(_\d+)?\.sitem$")

# De la tête aux pieds pour une tenue, du haut du corps aux chevilles pour une
# parure.
_ARMOUR_ORDER = "hvsgpb"
_JEWEL_ORDER = "derbpa"

_TYPE_FALLBACK = {
    ItemType.ANIMAL_MAT: Family.RAW_LOOTED,
    ItemType.NATURAL_MAT: Family.RAW_HARVESTED,
    ItemType.SYSTEM_MAT: Family.RAW_SYSTEM,
    ItemType.CATA: Family.CATALYST,
    ItemType.TELEPORTER: Family.TELEPORT,
}


def family(item: ItemInfo) -> Family:
    """Famille d'un objet, pour le regroupement à l'affichage."""
    known = _TYPE_FALLBACK.get(item.item_type)
    if known is not None:
        return known

    if item.item_type == ItemType.EQUIPMENT:
        equip = getattr(item, "equip", None)
        return Family.TOOL if equip is not None and equip.name == "TOOL" \
            else Family.EQUIPMENT

    sheet = (item.sheet or "").lower()
    for pattern, value in _PATTERNS:
        if pattern.match(sheet):
            return value
    return Family.OTHER


def material_key(item: ItemInfo) -> str:
    """Identifiant de matière, pour réunir les qualités d'une même matière."""
    match = _RAW_MATERIAL.match((item.sheet or "").lower())
    return match.group(1) if match else (item.sheet or "")


def outfit_key(item: ItemInfo) -> str | None:
    """Ce qui réunit deux pièces d'une même tenue, ou ``None``.

    Le jeu nomme les six pièces d'une armure de six façons — « Bottes Kara
    Paroks », « Casque Kara Parok » — et un tri par nom éparpillait donc chaque
    tenue parmi les autres. Le classer par fiche les remet ensemble.
    """
    sheet = (item.sheet or "").lower()
    match = _ARMOUR.match(sheet) or _JEWEL.match(sheet)
    if match is None:
        return None
    return match.group(1) + (match.group(3) or "")


def _piece_rank(item: ItemInfo) -> int:
    """Rang de la pièce dans sa tenue ; les inconnues passent après."""
    sheet = (item.sheet or "").lower()
    match = _ARMOUR.match(sheet)
    order = _ARMOUR_ORDER
    if match is None:
        match = _JEWEL.match(sheet)
        order = _JEWEL_ORDER
    if match is None:
        return 0
    rank = order.find(match.group(2))
    return len(order) if rank < 0 else rank


def sort_key(item: ItemInfo, name: str = "") -> tuple:
    """Clé de tri par famille.

    Les matières premières sont réunies par matière et classées du plus bas
    niveau au plus haut. Viennent ensuite les tenues et les parures, réunies
    par fiche, chacune à sa couleur et à sa qualité, et lues de la tête aux
    pieds ; puis ce qui ne fait partie d'aucun ensemble — armes, amplificateurs
    — par nom et par qualité, deux objets identiques de qualités différentes
    restant côte à côte.

    Les deux blocs sont séparés parce qu'ils ne se classent pas sur la même
    chose : mêler un code de fiche à un nom d'arme intercalait la Pique entre
    deux parures.

    `name` est attendu normalisé — minuscule et sans accents : le jeu écrit
    « Bracelet matis » avec une capitale et « bracelet zoraï » sans, et l'ordre
    brut des caractères mettrait toutes les minuscules après le Z.
    """
    group = family(item)
    quality = getattr(item, "quality", 0) or 0

    if group in (Family.RAW_HARVESTED, Family.RAW_LOOTED, Family.RAW_SYSTEM):
        return (int(group), material_key(item), quality, name)

    outfit = outfit_key(item)
    if outfit is not None:
        colour = int(getattr(item, "color", 0) or 0)
        return (int(group), 0, outfit, colour, quality, _piece_rank(item), name)

    return (int(group), 1, name or (item.sheet or ""), 0, quality)
