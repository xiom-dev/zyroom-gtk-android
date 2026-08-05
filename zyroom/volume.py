"""Calcul du volume des items et capacités des inventaires.

Portage fidèle de TRyzom.GetItemInfoFromName (UnitRyzom.pas) : le volume d'un
item = coefficient (déterminé par le motif de son nom de fiche) × |taille de
pile|. Les capacités des inventaires viennent de UnitConfig.pas.
"""
from __future__ import annotations

import re

from .models import (ItemClass, ItemEcosystem, ItemEquip, ItemInfo, ItemSkin,
                     ItemType)

# Type d'armure selon la lettre après « ic.a »
_ARMOR_EQUIP = {"l": ItemEquip.LIGHT_ARMOR, "c": ItemEquip.LIGHT_ARMOR,
                "b": ItemEquip.LIGHT_ARMOR, "g": ItemEquip.LIGHT_ARMOR,
                "p": ItemEquip.LIGHT_ARMOR, "s": ItemEquip.LIGHT_ARMOR,
                "v": ItemEquip.LIGHT_ARMOR, "m": ItemEquip.MEDIUM_ARMOR,
                "h": ItemEquip.HEAVY_ARMOR}

# Écosystème d'un équipement selon la lettre après « ic »
_EQUIP_ECOSYS = {"t": ItemEcosystem.LAKES, "f": ItemEcosystem.DESERT,
                 "m": ItemEcosystem.FOREST, "z": ItemEcosystem.JUNGLE}
# Écosystème d'une matière selon la lettre du motif
_MAT_ECOSYS = {"c": ItemEcosystem.COMMON, "g": ItemEcosystem.COMMON,
               "p": ItemEcosystem.PRIME, "d": ItemEcosystem.DESERT,
               "f": ItemEcosystem.FOREST, "l": ItemEcosystem.LAKES,
               "j": ItemEcosystem.JUNGLE}
_NATURAL_CLASS = {"a": ItemClass.BASIC, "b": ItemClass.BASIC, "c": ItemClass.FINE,
                  "d": ItemClass.CHOICE, "e": ItemClass.EXCELLENT, "f": ItemClass.SUPREME}
_ANIMAL_CLASS = {"a": ItemClass.BASIC, "b": ItemClass.FINE, "c": ItemClass.CHOICE,
                 "d": ItemClass.EXCELLENT, "e": ItemClass.SUPREME, "f": ItemClass.SUPREME}

# --- Capacités maximales (UnitConfig.pas) ---------------------------------
CAP_BAG = 300
CAP_ROOM = 2000
CAP_MEKTOUB = 500
CAP_MOUNT = 300
CAP_ZIG = 150

# --- Listes de noms (UnitRyzom.pas) ---------------------------------------
_MAT_JOBS = {"lucky_flower.sitem", "protect_amber.sitem",
             "water_barrel.sitem", "tools_ticket.sitem"}
_MAT_GUILD_CHEST = {"mp_hard.sitem", "mp_soft.sitem", "mp_colonne.sitem",
                    "mp_ornement.sitem", "mp_revetement.sitem"}

# --- Expressions régulières (identiques à _EXPR_* du Delphi) --------------
_EXPR_NATURAL_MAT = re.compile(r"^m\d{4}dxa([pcdfljg])([a-f])01\.sitem")
_EXPR_ANIMAL_MAT = re.compile(r"^m\d{4}.{3}([pcdfljg])([a-f])01\.sitem")
_EXPR_SYSTEM_MAT = re.compile(r"(system_mp_?|mp_kami_ep2_|mp_karavan_ep2_)(\w*)\.sitem")
_EXPR_TOOL = re.compile(r"^(ico(kar|kam|mar|gen)t|sfxitforage|it).*\.sitem")
_EXPR_EQUIPMENT = re.compile(r"^ic(.).*(..)\.sitem")
_EXPR_EQUIPMENT_ARMOR = re.compile(r"^ic.a([lmhcbgpsv]).*")
_EXPR_EQUIPMENT_SHIELD = re.compile(r"^ic(?:.|ka[rm])s([bs]).*")
_EXPR_EQUIPMENT_AMPLIFIER = re.compile(r"^ic.+m2ms.*")
_EXPR_EQUIPMENT_WEAPON = re.compile(r"^ic.+([rm])([12])(..).*")
_EXPR_EQUIPMENT_AMMO = re.compile(r"^ic.p([12][ablpr]).*\.sitem")
_EXPR_EQUIPMENT_JEWEL = re.compile(r"^ic.j.*")
_EXPR_BANDIT_CHEST = re.compile(r"compo_.*mark\d\.sitem")


def _classify(item: ItemInfo) -> tuple[ItemType, float]:
    """(type, coefficient de volume) d'un item, d'après son nom de fiche.

    Reproduit l'enchaînement de tests de GetItemInfoFromName."""
    name = item.sheet
    coef = 0.0
    itype = ItemType.OTHER
    is_other = True  # équivaut à "ItemType = itOther"

    # Catalyseur
    if name.startswith("ixpca0"):
        is_other = False
        itype = ItemType.CATA
        coef = 0.01

    # Téléporteur (coef 0)
    if name.startswith("tp_ka"):
        is_other = False
        itype = ItemType.TELEPORTER

    # Outil
    if is_other and _EXPR_TOOL.match(name) and "_sap_recharge" not in name:
        is_other = False
        itype = ItemType.EQUIPMENT
        item.equip = ItemEquip.TOOL
        coef = 10.0

    # Équipement
    m_eq = _EXPR_EQUIPMENT.match(name)
    if is_other and m_eq:
        is_other = False
        itype = ItemType.EQUIPMENT
        item.ecosystem = _EQUIP_ECOSYS.get(m_eq.group(1)[0], ItemEcosystem.COMMON)
        g2 = m_eq.group(2)
        item.skin = {"2": ItemSkin.SKIN2, "3": ItemSkin.SKIN3}.get(g2[1], ItemSkin.SKIN1)
        equip_found = False

        # Bouclier
        m = _EXPR_EQUIPMENT_SHIELD.match(name)
        if not equip_found and m:
            if m.group(1) == "b":
                item.equip = ItemEquip.BUCKLER
                coef = 5.0
                equip_found = True
            elif m.group(1) == "s":
                item.equip = ItemEquip.SHIELD
                coef = 20.0 if name == "icbss_pvp.sitem" else 10.0
                equip_found = True

        # Armure
        if not equip_found:
            m = _EXPR_EQUIPMENT_ARMOR.match(name)
            if m:
                item.equip = _ARMOR_EQUIP.get(m.group(1), ItemEquip.LIGHT_ARMOR)
                coef = 20.0 if name.startswith("iccah") else 7.0
                equip_found = True

        # Amplificateur
        if not equip_found and _EXPR_EQUIPMENT_AMPLIFIER.match(name):
            item.equip = ItemEquip.AMPLIFIER
            coef = 10.0
            equip_found = True

        # Arme
        if not equip_found:
            m = _EXPR_EQUIPMENT_WEAPON.match(name)
            if m:
                kind, hands, tail = m.group(1), m.group(2), m.group(3)
                if kind == "m":  # mêlée
                    item.equip = ItemEquip.WEAPON_MELEE
                    if hands == "1":
                        coef = 5.0 if tail == "pd" else 10.0
                    elif hands == "2":
                        coef = 15.0
                elif kind == "r":  # distance
                    item.equip = ItemEquip.WEAPON_RANGE
                    if hands == "1":
                        coef = 10.0
                    elif hands == "2":
                        coef = {"a": 30.0, "b": 15.0, "r": 15.0, "l": 30.0}.get(tail[0], 0.0)
                equip_found = True

        # Munition
        if not equip_found:
            m = _EXPR_EQUIPMENT_AMMO.match(name)
            if m:
                item.equip = ItemEquip.AMMO
                g = m.group(1)
                if g[0] == "1":
                    coef = 0.04
                elif g[0] == "2":
                    coef = {"a": 5.0, "b": 0.1, "r": 0.1, "l": 15.0}.get(g[1], 0.0)
                equip_found = True

        # Bijou
        if not equip_found and _EXPR_EQUIPMENT_JEWEL.match(name):
            item.equip = ItemEquip.JEWEL
            coef = 2.0
            equip_found = True

        # Autres équipements
        if not equip_found:
            if name.startswith("ic_candy_stick"):
                coef = 30.0
            elif name.startswith("ic_halloween_stick"):
                coef = 30.0
            elif name.startswith("ic_anlor_helmet01"):
                coef = 7.0

    # Matières naturelles
    m_nat = _EXPR_NATURAL_MAT.match(name)
    if is_other and m_nat:
        is_other = False
        itype = ItemType.NATURAL_MAT
        coef = 0.5
        item.ecosystem = _MAT_ECOSYS.get(m_nat.group(1), ItemEcosystem.COMMON)
        item.item_class = _NATURAL_CLASS.get(m_nat.group(2), ItemClass.UNKNOWN)
    # Matières animales
    m_ani = _EXPR_ANIMAL_MAT.match(name)
    if is_other and m_ani:
        is_other = False
        itype = ItemType.ANIMAL_MAT
        coef = 0.5
        item.ecosystem = _MAT_ECOSYS.get(m_ani.group(1), ItemEcosystem.COMMON)
        item.item_class = _ANIMAL_CLASS.get(m_ani.group(2), ItemClass.UNKNOWN)

    # Autres (type toujours itOther)
    if is_other:
        specials = {
            "teddyubo.sitem": 5.0, "xmas_gingeryubo.sitem": 5.0, "louche.sitem": 5.0,
            "if1.sitem": 15.0, "if2.sitem": 5.0, "if3.sitem": 9.0, "winch.sitem": 5.0,
            "s2e1_salins.sitem": 0.5, "s2e1_seve_suc.sitem": 0.5, "ulo_4.sitem": 1.0,
            "event_magnetized_amber.sitem": 0.5, "rite_ranger_map_book.sitem": 0.5,
            "anniversary_dance_scroll.sitem": 0.5,
        }
        if "pre_order.sitem" in name:
            coef = 5.0
        if name in specials:
            coef = specials[name]
        if name.startswith("ipoc_"):
            coef = 1.0
        if name.startswith("ipm"):
            coef = 1.0
        if name.startswith("ipk_"):
            coef = 1.0
        if name in _MAT_JOBS:
            coef = 1.0
        if _EXPR_BANDIT_CHEST.search(name):
            coef = 0.5
        if name in _MAT_GUILD_CHEST:
            coef = 0.1
        if name in ("icbm1sa_2.sitem", "icbm1bs.sitem"):
            itype = ItemType.EQUIPMENT
            item.ecosystem = ItemEcosystem.COMMON
            item.skin = ItemSkin.SKIN3
            coef = 20.0
        if name.startswith("ikaracp_ep") or name.startswith("ikamacp_ep"):
            itype = ItemType.EQUIPMENT
            item.ecosystem = ItemEcosystem.COMMON
            item.skin = ItemSkin.SKIN3
            coef = 7.0
        # Matières système
        m_sys = _EXPR_SYSTEM_MAT.search(name)
        if m_sys:
            itype = ItemType.SYSTEM_MAT
            item.ecosystem = ItemEcosystem.COMMON
            item.item_class = ItemClass.BASIC
            suffix = m_sys.group(2)
            for key, cls in (("fine", ItemClass.FINE), ("choice", ItemClass.CHOICE),
                             ("xl", ItemClass.EXCELLENT), ("excellent", ItemClass.EXCELLENT),
                             ("supreme", ItemClass.SUPREME), ("extra", ItemClass.SUPREME)):
                if suffix.startswith(key):
                    item.item_class = cls
            if name == "system_mp_loot.sitem":
                coef = 0.5

    return itype, coef


def classify(item: ItemInfo) -> None:
    """Détermine le type de l'item et calcule son volume (met à jour l'item)."""
    itype, coef = _classify(item)
    item.item_type = itype
    item.volume = coef * abs(item.stack)


def item_volume(item: ItemInfo) -> float:
    """Volume d'un item = coef × |taille de pile|."""
    return _classify(item)[1] * abs(item.stack)


def animal_capacity(creature_sheet: str) -> tuple[int, str]:
    """(capacité, type) d'un animal d'après sa fiche de créature.
    type ∈ {'mektoub', 'mount', 'zig'} (cf. UnitFormInvent.pas)."""
    if creature_sheet.startswith("chj"):
        return CAP_MEKTOUB, "mektoub"
    if "zig" in creature_sheet:
        return CAP_ZIG, "zig"
    return CAP_MOUNT, "mount"
