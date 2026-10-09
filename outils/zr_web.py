"""Le pont entre la page xiom.be/zyroom et le code de ZyRoom-GTK.

Tourne dans Pyodide, dans le Web Worker de `zyroom/travail.js`. La page
recoit les flux de l'API (personnage directement, guilde par zyroom.php) et
les passe ici : la lecture, les noms, les categories, les volumes, les tris
sont ceux de l'application, sans copie. Seul ce que window.py fait au milieu
de son interface GTK -- l'infobulle, le filtre, la ligne d'etat -- est
reecrit, au plus pres, dans `entite()` et dans la page.

Range dans `zyroom.zip` par `outils/page-zyroom.py`.
"""
from __future__ import annotations

import json
import unicodedata

from zyroom import ryzom_api, sorting
from zyroom.categorydb import CategoryDb
from zyroom.models import (CLASS_NAMES, ECOSYSTEM_NAMES, EQUIP_NAMES, ItemType,
                           categorie_item)
from zyroom.movements import sans_parenthese
from zyroom.namedb import NameDb, nom_anglais
from zyroom.sheetdb import SheetDb
from zyroom import enchantements

#: Ou le zip est deballe dans Pyodide.
RACINE = "/zr/zyroom"

noms = NameDb("/zr/names.json")
fiches = SheetDb()
categories = CategoryDb()

#: Les gouttes, comme specialites.SPECIALITES (module GTK, non importable ici).
SPECIALITES = (
    ("hp_buff", "Vie", "#e2696a"),
    ("sap_buff", "Sève", "#4caf50"),
    ("sta_buff", "Endurance", "#a97fd0"),
    ("focus_buff", "Concentration", "#4a90d9"),
)

#: Les cles de tri, comme window._SORT_KEYS (l'index est celui du menu).
TRIS = {
    1: lambda it, nom: sorting.sort_key(it, _norm(nom), categories.categories),
    2: lambda it, nom: int(it.ecosystem),
    3: lambda it, nom: int(it.item_class),
    4: lambda it, nom: it.quality,
    5: lambda it, nom: it.volume,
    6: lambda it, nom: it.stack,
    7: lambda it, nom: it.price,
    8: lambda it, nom: _norm(nom),
}


def _norm(texte: str) -> str:
    """Comme ui_commun._norm : minuscule sans accents."""
    texte = unicodedata.normalize("NFKD", texte)
    return "".join(c for c in texte if not unicodedata.combining(c)).lower()


def demarrer() -> str:
    noms.load_cache()
    fiches.load(f"{RACINE}/data/sheetid.csv")
    categories.load(f"{RACINE}/data/category.csv")
    return json.dumps({
        "noms": len(noms._map), "classes": CLASS_NAMES, "ecosystemes": ECOSYSTEM_NAMES,
        "equipements": EQUIP_NAMES, "specialites": [[l, c] for _a, l, c in SPECIALITES],
    }, ensure_ascii=False)


def _infobulle(it, nom: str) -> list[str]:
    """Comme window._item_tooltip, sans la surveillance (pas encore en ligne)."""
    lignes = [nom]
    if it.quality:
        lignes.append(f"Qualité : {it.quality}")
    if it.stack:
        lignes.append(f"Quantité : {it.stack}")
    if it.item_type == ItemType.EQUIPMENT and it.hp:
        lignes.append(f"Durabilité : {it.hp} / {it.hp_max}" if it.hp_max
                      else f"Durabilité : {it.hp}")
    if it.volume:
        lignes.append(f"Volume : {it.volume:.2f}")
    if it.price:
        lignes.append(f"Prix : {it.price:,.0f} dappers".replace(",", " "))
    if it.continent:
        lignes.append(f"Continent : {it.continent}")
    if it.locked:
        lignes.append("🔒 Protégé")
    return lignes


def _objet(it) -> dict:
    nom = noms.name(it.sheet)
    bonus = [[libelle, getattr(it, attribut), couleur]
             for attribut, libelle, couleur in SPECIALITES if getattr(it, attribut, 0)]
    sort = enchantements.resume(it, noms.name)
    enchant = ""
    if sort:
        enchant = f"Enchantement : {sort}"
        if it.sap_charges:
            enchant += f"\nCharges de sève : {it.sap_charges}"
        if it.enchant_cost:
            enchant += f" (coût {abs(it.enchant_cost)})"
    brique = enchantements.brique_icone(it)
    return {
        "fiche": it.sheet, "nom": nom, "icone": ryzom_api.item_icon_url(it),
        "cle": _norm(f"{nom} {it.sheet} {nom_anglais(it.sheet)}"),
        "categorie": categorie_item(it, nom),
        "q": it.quality, "n": it.stack, "vol": it.volume, "prix": it.price,
        "eco": int(it.ecosystem), "classe": int(it.item_class),
        "equip": int(it.equip) if it.item_type == ItemType.EQUIPMENT else -1,
        "cadenas": it.locked, "vente": it.expires > 0,
        "bonus": bonus, "bulle": _infobulle(it, nom), "enchant": enchant,
        "sort": ryzom_api.brique_icon_url(brique) if brique else "",
    }


def _ordres(items: list) -> dict:
    """Pour chaque tri, l'ordre des objets, croissant et decroissant.

    Les deux sont calcules ici plutot que l'un renverse dans la page : un tri
    decroissant de Python garde l'ordre d'origine des egaux, ce que renverser
    l'ordre croissant ne ferait pas.
    """
    nommes = [(i, it, noms.name(it.sheet)) for i, it in enumerate(items)]
    ordres = {}
    for rang, cle in TRIS.items():
        for sens, inverse in (("asc", False), ("desc", True)):
            ordres[f"{rang}{sens}"] = [i for i, _it, _n in
                                       sorted(nommes, key=lambda x: cle(x[1], x[2]),
                                              reverse=inverse)]
    return ordres


def entite(xml: str, sorte: str) -> str:
    """Un flux de l'API, lu par ryzom_api, pret a afficher."""
    lire = ryzom_api.parse_character if sorte == "character" else ryzom_api.parse_guild
    try:
        ent = lire(xml.encode("utf-8"), fiches.name)
    except ryzom_api.ApiError as exc:
        return json.dumps({"erreur": str(exc)}, ensure_ascii=False)
    return json.dumps({
        "sorte": ent.kind, "id": ent.entity_id, "nom": ent.name, "guilde": ent.guild,
        "argent": ent.money, "motd": ent.motd, "portrait": ent.portrait_url,
        "connexion": ent.lastlogin, "deconnexion": ent.lastlogout,
        "calcul": ent.created,
        "contenants": [{
            "cle": inv.key, "nom": sans_parenthese(inv.label), "capacite": inv.capacity,
            "volume": inv.total_volume, "objets": [_objet(it) for it in inv.items],
            "ordres": _ordres(inv.items),
        } for inv in ent.inventories],
    }, ensure_ascii=False)


def saison(xml: str) -> str:
    return json.dumps(ryzom_api.parse_time(xml.encode("utf-8")), ensure_ascii=False)
