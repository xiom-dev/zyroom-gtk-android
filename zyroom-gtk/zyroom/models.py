"""Modèle de domaine Ryzom et parsing d'items depuis le XML de l'API.

Portage fidèle de la logique de `UnitRyzom.pas` / `RyzomApi.pas` (Delphi) :
  - énumération des couleurs d'item (ordre identique à l'original)
  - extraction des champs d'un noeud <item> du flux XML
  - construction du nom de fichier de cache d'icône, identique bit à bit à
    l'original -> permet de réutiliser les caches d'icônes existants.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from xml.etree.ElementTree import Element


class ItemColor(IntEnum):
    """Couleurs d'item. L'ordre (valeur entière) doit rester identique au
    Delphi car il est envoyé tel quel à l'API item_icon.php (&c=<n>) et sert
    aussi dans le nom du fichier de cache."""
    RED = 0
    BEIGE = 1
    GREEN = 2
    TURQUOISE = 3
    BLUE = 4
    PURPLE = 5
    WHITE = 6
    BLACK = 7
    NONE = 8


class ItemType(IntEnum):
    """Type d'item (ordre identique à TItemType du Delphi)."""
    ANIMAL_MAT = 0
    NATURAL_MAT = 1
    SYSTEM_MAT = 2
    CATA = 3
    EQUIPMENT = 4
    TELEPORTER = 5
    OTHER = 6


class ItemClass(IntEnum):
    BASIC = 0
    FINE = 1
    CHOICE = 2
    EXCELLENT = 3
    SUPREME = 4
    UNKNOWN = 5


class ItemEcosystem(IntEnum):
    COMMON = 0
    PRIME = 1
    DESERT = 2
    JUNGLE = 3
    FOREST = 4
    LAKES = 5
    UNKNOWN = 6


class ItemSkin(IntEnum):
    SKIN1 = 0
    SKIN2 = 1
    SKIN3 = 2
    UNKNOWN = 3


class ItemEquip(IntEnum):
    """Sous-type d'équipement (ordre identique à TItemEquip du Delphi)."""
    LIGHT_ARMOR = 0
    MEDIUM_ARMOR = 1
    HEAVY_ARMOR = 2
    WEAPON_MELEE = 3
    WEAPON_RANGE = 4
    AMPLIFIER = 5
    JEWEL = 6
    BUCKLER = 7
    SHIELD = 8
    TOOL = 9
    AMMO = 10
    OTHER = 11


TYPE_NAMES = ("Matière animale", "Matière naturelle", "Matière système",
              "Catalyseur", "Équipement", "Téléporteur", "Autre")
EQUIP_NAMES = ("Armure légère", "Armure moyenne", "Armure lourde", "Arme mêlée",
               "Arme distance", "Amplificateur", "Bijou", "Bouclier",
               "Grand bouclier", "Outil", "Munition", "Autre")


# Libellés d'affichage (index = valeur de l'énum)
CLASS_NAMES = ("Basique", "Fine", "Choix", "Excellente", "Suprême", "—")
ECOSYSTEM_NAMES = ("Commun", "Primes Racines", "Désert", "Jungle", "Forêt", "Lacs", "—")
COLOR_NAMES = ("inconnu", "beige", "noir", "bleu", "vert", "violet", "rouge",
               "turquoise", "blanc")
# Caractéristiques de matière (_MAT_SPEC) et catégories (_MAT_CATEGORY) du Delphi
MAT_CATEGORY = ("Toutes", "Lame", "Pointe", "Masse", "Contrepoids", "Manche",
                "Munition (balle)", "Canon", "Coque d'armure", "Enveloppe de munition",
                "Doublure", "Explosif", "Rembourrage", "Percuteur", "Attache d'armure",
                "Détente", "Sertissage", "Poignée", "Vêtement", "Bijou", "Focus magique")
MAT_SPEC = ("Toutes", "Durabilité", "Légèreté", "Charge de sève", "Dégâts", "Vitesse",
            "Portée", "Mod. esquive", "Mod. parade", "Mod. esquive adverse",
            "Mod. parade adverse", "Facteur de protection", "Prot. tranchant max.",
            "Prot. contondant max.", "Prot. perforant max.", "Prot. acide", "Prot. froid",
            "Prot. pourriture", "Prot. feu", "Prot. onde de choc", "Prot. poison",
            "Prot. électricité", "Vit. sort élémentaire", "Puiss. élémentaire",
            "Vit. affliction off.", "Puiss. affliction off.", "Vit. affliction déf.",
            "Puiss. affliction déf.", "Vit. soin", "Puiss. soin", "Rés. désert",
            "Rés. forêt", "Rés. lacs", "Rés. jungle", "Rés. Primes Racines")


# Correspondance 6e lettre du nom -> couleur, pour l'armure de réfugié "icra..."
# (cf. UnitRyzom.pas, GetItemInfoFromXML).
PROTECTION_FR = {"acid": "Acide", "cold": "Froid", "fire": "Feu",
                 "rot": "Pourriture", "shockwave": "Onde de choc",
                 "poison": "Poison", "electricity": "Électricité"}
_RESIST_ORDER = ("desert", "forest", "lacustre", "jungle", "primaryroot")
RESISTANCE_FR = {"desert": "Désert", "forest": "Forêt", "lacustre": "Lacs",
                 "jungle": "Jungle", "primaryroot": "Primes Racines"}
_PROTECTION_ORDER = ("acid", "cold", "fire", "rot", "shockwave", "poison", "electricity")

_REFUGEE_COLOR = {
    "a": ItemColor.BLACK,
    "e": ItemColor.BEIGE,
    "g": ItemColor.GREEN,
    "r": ItemColor.RED,
    "t": ItemColor.TURQUOISE,
    "u": ItemColor.BLUE,
    "v": ItemColor.PURPLE,
    "w": ItemColor.WHITE,
}


def to_item_color(value: str) -> ItemColor:
    """Équivalent de ToItemColor : entier depuis le XML, défaut NONE (8)."""
    try:
        return ItemColor(int(value))
    except (ValueError, TypeError):
        return ItemColor.NONE


@dataclass
class ItemInfo:
    """Sous-ensemble de TItemInfo utile à l'affichage (MVP).

    Les caractéristiques de craft détaillées (dégâts, protections, résistances,
    amplis...) seront ajoutées dans un jalon ultérieur."""
    sheet: str = ""            # nom de fiche, ex "m0067ckdpd01.sitem"
    item_id: str = ""          # identifiant unique de l'item
    slot: int = 0
    color: ItemColor = ItemColor.NONE
    quality: int = 0
    stack: int = 0             # taille de la pile (ItemSize)
    locked: bool = False
    sap: bool = False          # possède une charge de sève
    sap_charges: int = 0       # charge actuelle (flux personnage seul)
    enchant_cost: int = 0      # cout en seve d'un lancer
    enchant_bricks: list = field(default_factory=list)  # les .sbrick du sort
    destroyed: bool = False
    hp: int = 0                # durabilité restante (pour l'équipement)
    hp_max: int = 0            # durabilite d'origine, fixee au craft
    volume: float = 0.0        # rempli après parsing (voir volume.py)
    item_type: "ItemType" = ItemType.OTHER  # rempli par volume.classify
    # Champs des items en vente (shop)
    price: float = 0.0
    continent: str = ""
    expires: int = 0           # timestamp Unix d'expiration (0 = pas en vente)
    # Caractéristiques détaillées (craft)
    weight: float = 0.0
    item_class: "ItemClass" = ItemClass.UNKNOWN
    ecosystem: "ItemEcosystem" = ItemEcosystem.UNKNOWN
    skin: "ItemSkin" = ItemSkin.UNKNOWN
    equip: "ItemEquip" = ItemEquip.OTHER
    hp_buff: int = 0
    sap_buff: int = 0
    sta_buff: int = 0
    focus_buff: int = 0
    c_dmg: int = 0
    c_speed: int = 0
    c_range: int = 0
    c_dodge: int = 0
    c_parry: int = 0
    c_adv_dodge: int = 0
    c_adv_parry: int = 0
    c_factor_prot: float = 0.0
    c_slash: int = 0
    c_blunt: int = 0
    c_pierce: int = 0
    protections: list = field(default_factory=list)   # [(nom, valeur), ...] (bijoux)
    resistances: list = field(default_factory=list)   # [(nom, valeur), ...] (bijoux)
    a_elem_speed: int = 0
    a_elem_power: int = 0
    a_off_speed: int = 0
    a_off_power: int = 0
    a_heal_speed: int = 0
    a_heal_power: int = 0
    a_def_speed: int = 0
    a_def_power: int = 0
    # Matière : catégories et specs (remplis à la demande via categorydb)
    mat_category1: int = 0
    mat_category2: int = 0
    mat_specs1: list = field(default_factory=list)    # [(index_spec, niveau 1-5), ...]
    mat_specs2: list = field(default_factory=list)
    mat_colors: list = field(default_factory=list)    # [c1, c2, c3] (indices _MAT_COLOR)

    @property
    def cache_filename(self) -> str:
        """Nom du fichier d'icône en cache, identique à l'original
        (UnitRyzom.pas:976) : `<sheet>.c<col>q<qual>s<pile>d<détruit>l<verrou>s<sève>.png`."""
        return "{sheet}.c{c}q{q}s{s}d{d}l{l}s{sap}.png".format(
            sheet=self.sheet,
            c=int(self.color),
            q=self.quality,
            s=self.stack,
            d=1 if self.destroyed else 0,
            l=1 if self.locked else 0,
            sap=1 if self.sap else 0,
        )


def item_sig(item: "ItemInfo") -> str:
    """Signature d'un item pour la surveillance / la détection de mouvements."""
    return f"{item.sheet}|{item.quality}"


def _text(node: Element, path: str) -> str:
    """Renvoie le texte d'un sous-noeud (ou attribut via '@'), '' si absent."""
    if path.startswith("@"):
        return node.get(path[1:], "") or ""
    found = node.find(path)
    return (found.text or "") if found is not None else ""


def _cp_val(node: Element, name: str) -> str:
    """Attribut @value du noeud craftparameters/<name> (ElementTree ne sait pas
    sélectionner un attribut directement)."""
    el = node.find(f".//craftparameters/{name}")
    return el.get("value", "") if el is not None else ""


def _cp_text(node: Element, name: str) -> str:
    el = node.find(f".//craftparameters/{name}")
    return (el.text or "") if el is not None else ""


def _float(value: str) -> float:
    try:
        return float(value.replace(",", "."))
    except (ValueError, AttributeError):
        return 0.0


def _int(value: str) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def _parse_craft(node: Element, item: "ItemInfo") -> None:
    """Lit les caractéristiques de craft (portage de GetItemInfoFromXML)."""
    item.weight = _float(_cp_val(node, "weight"))
    # La durabilite d'origine, que le jeu affiche en second nombre : `<hp>`
    # dit ce qui reste, `durability` ce qu'il y avait au sortir de la forge.
    item.hp_max = _int(_cp_val(node, "durability"))

    # Classe déduite de l'énergie (statenergy)
    energy = _cp_text(node, "statenergy")
    if energy:
        e = round(_float(energy), 2)
        if e <= 0.2:
            item.item_class = ItemClass.BASIC
        elif e <= 0.35:
            item.item_class = ItemClass.FINE
        elif e <= 0.5:
            item.item_class = ItemClass.CHOICE
        elif e <= 0.65:
            item.item_class = ItemClass.EXCELLENT
        else:
            item.item_class = ItemClass.SUPREME

    # Bonus
    item.hp_buff = _int(_cp_text(node, "hpbuff"))
    item.sap_buff = _int(_cp_text(node, "sapbuff"))
    item.sta_buff = _int(_cp_text(node, "stabuff"))
    item.focus_buff = _int(_cp_text(node, "focusbuff"))

    # Combat
    item.c_dmg = _int(_cp_val(node, "dmg"))
    item.c_speed = _int(_cp_val(node, "speed"))
    item.c_range = _int(_cp_val(node, "range"))
    item.c_dodge = _int(_cp_val(node, "dodgemodifier"))
    item.c_parry = _int(_cp_val(node, "parrymodifier"))
    item.c_adv_dodge = _int(_cp_val(node, "adversarydodgemodifier"))
    item.c_adv_parry = _int(_cp_val(node, "adversaryparrymodifier"))
    item.c_factor_prot = _float(_cp_val(node, "protectionfactor"))
    item.c_slash = _int(_cp_val(node, "maxslashingprotection"))
    item.c_blunt = _int(_cp_val(node, "maxbluntprotection"))
    item.c_pierce = _int(_cp_val(node, "maxpiercingprotection"))

    # Protections des bijoux (jusqu'à 3)
    for i in (1, 2, 3):
        ptype = _cp_text(node, f"protection{i}")
        if ptype not in _PROTECTION_ORDER:
            continue
        val_attr = _cp_val(node, f"protection{i}factor")
        if val_attr:
            value = _int(val_attr)
        else:
            factor = _cp_text(node, f"protection{i}factor")
            value = int(_float(factor) * 8) if factor else 0
        item.protections.append((PROTECTION_FR[ptype], value))

    # Résistances des bijoux
    for r in _RESIST_ORDER:
        v = _cp_val(node, f"{r}resistancefactor")
        if v:
            fv = _float(v)
            if fv > 0:
                item.resistances.append((RESISTANCE_FR[r], fv))

    # Amplificateur magique
    item.a_elem_speed = _int(_cp_val(node, "elementalcastingtimefactor"))
    item.a_elem_power = _int(_cp_val(node, "elementalpowerfactor"))
    item.a_off_speed = _int(_cp_val(node, "offensiveafflictioncastingtimefactor"))
    item.a_off_power = _int(_cp_val(node, "offensiveafflictionpowerfactor"))
    item.a_heal_speed = _int(_cp_val(node, "healcastingtimefactor"))
    item.a_heal_power = _int(_cp_val(node, "healpowerfactor"))
    item.a_def_speed = _int(_cp_val(node, "defensiveafflictioncastingtimefactor"))
    item.a_def_power = _int(_cp_val(node, "defensiveafflictionpowerfactor"))


def parse_item(node: Element, resolve_sheet=None) -> ItemInfo:
    """Extrait un ItemInfo d'un noeud <item> (ou <shopitem>) du flux XML.

    Portage de TRyzom.GetItemInfoFromXML (partie affichage). `resolve_sheet`
    est une fonction facultative name('#123') -> 'xxx.sitem' pour les rares
    fiches référencées par identifiant numérique."""
    item = ItemInfo()

    # Nom de fiche — parfois un identifiant numérique préfixé par '#'
    name = _text(node, ".//sheet")
    if name.startswith("#") and resolve_sheet is not None:
        name = resolve_sheet(name)
    item.sheet = name

    item.item_id = _text(node, "@id")

    slot = _text(node, "@slot")
    if slot:
        item.slot = int(slot)

    # Couleur : présente dans craftparameters/color pour l'équipement craftable
    color_val = _text(node, ".//craftparameters/color")
    if color_val:
        item.color = to_item_color(color_val)

    # Cas particulier : armure de réfugié "icra..." -> couleur = 6e lettre
    if item.color == ItemColor.NONE and item.sheet.startswith("icra") and len(item.sheet) >= 6:
        item.color = _REFUGEE_COLOR.get(item.sheet[5], ItemColor.NONE)

    # Qualité — un "1" est ramené à 0 (évite un "1" inutile sur beaucoup d'icônes)
    quality = _text(node, ".//quality")
    if quality:
        q = int(quality)
        item.quality = 0 if q == 1 else q

    # Taille de pile
    stack = _text(node, "stack")
    if stack:
        item.stack = int(stack)

    locked = _text(node, ".//locked")
    if locked:
        item.locked = int(locked) > 0

    # Charge de sève : présence du noeud sapload (sauf sorts cristallisés)
    charge = _text(node, "sapload")
    if charge and item.sheet.lower() != "crystalized_spell.sitem":
        item.sap = True
        item.sap_charges = _int(charge)

    # L'enchantement : le sort grave dans l'objet, decrit par ses briques.
    #
    # **Le flux personnage seul le porte.** Les coffres de guilde n'en
    # transmettent rien — verifie sur 3138 objets de deux guildes, pas un seul
    # noeud. Le champ reste donc vide pour eux, et l'affichage n'en montre rien
    # plutot que de laisser croire qu'aucune arme n'est enchantee.
    enchantement = node.find("enchantment")
    if enchantement is not None:
        item.enchant_cost = _int(enchantement.get("cost", "0"))
        item.enchant_bricks = [brique.text for brique in enchantement.findall("sbrick")
                               if brique.text]

    hp = _text(node, ".//hp")
    if hp:
        item.hp = int(hp)
        item.destroyed = item.hp == 1

    # Champs des items en vente (présents seulement dans le shop)
    price = _text(node, ".//price")
    if price:
        try:
            item.price = float(price)
        except ValueError:
            pass
    continent = _text(node, ".//continent")
    if continent:
        item.continent = continent.capitalize()
    timestamp = _text(node, ".//timestamp")
    if timestamp:
        try:
            # expiration = date de mise en vente + 7 jours + 2 heures (cf. Delphi)
            item.expires = int(timestamp) + 7 * 86400 + 2 * 3600
        except ValueError:
            pass

    _parse_craft(node, item)
    return item
