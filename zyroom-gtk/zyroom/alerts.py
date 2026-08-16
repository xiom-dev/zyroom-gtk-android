"""Alertes : ce que la cloche a le droit de dire.

La règle tient en une phrase : **la cloche ne porte que ce qu'on lui a demandé
de guetter**. Quatre surveillances, toutes réglées par le joueur :

  - **Objet surveillé** : un seuil posé à la main sur une matière (quantité
    minimale) ou sur un équipement (durabilité), et le signalement de l'objet
    surveillé qui a disparu.
  - **Volume** : un contenant dépasse le seuil de remplissage des options.
  - **Vente** : une mise en vente expire bientôt.
  - **Saison** : elle tourne dans moins de tant d'heures.

Les **mouvements** d'objets, eux, ne sont pas des alertes : personne ne les a
demandés, et ranger douze matières faisait sonner douze fois. Ils vont au
journal, qui les garde datés — voir `movements.py`. L'instantané qui sert à
les calculer est construit ici (`build_snapshot`), c'est tout.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass

from .models import item_sig
from .watch import KIND_DURABILITY


@dataclass
class Alert:
    kind: str          # 'quantity' | 'durability' | 'unfound' | 'volume' | 'sales' | 'season'
    title: str
    detail: str


# ------------------------------------------------------------------ Volume
def volume_alerts(entity, threshold: int) -> list[Alert]:
    """Inventaires dont le remplissage atteint le seuil (%)."""
    out = []
    for inv in entity.inventories:
        if inv.capacity <= 0:
            continue
        pct = inv.total_volume / inv.capacity * 100.0
        if pct >= threshold:
            out.append(Alert(
                "volume",
                f"{inv.label} : {pct:.0f}% plein",
                f"{inv.total_volume:.0f} / {inv.capacity} de volume",
            ))
    return out


# ------------------------------------------------ Instantané (pour le journal)
def build_snapshot(entity) -> dict:
    """Instantané {clé_inventaire: {signature: quantité}}.
    signature = 'sheet|qualité' ; quantité = somme des piles.

    Les contenants masqués en sont exclus, et pas seulement vidés : un
    instantané antérieur où le coffre était garni ferait sinon apparaître, au
    premier relevé suivant, un retrait par item — soit exactement la liste
    qu'on masque. `movements.diff` ne parcourant que les clés du nouvel
    instantané, l'absence suffit à les tenir hors du journal.
    """
    snap: dict[str, dict[str, int]] = {}
    for inv in entity.inventories:
        if getattr(inv, "masked", False):
            continue
        counts: dict[str, int] = {}
        for it in inv.items:
            sig = item_sig(it)
            counts[sig] = counts.get(sig, 0) + max(it.stack, 1)
        snap[inv.key] = counts
    return snap


# ------------------------------------------ Surveillance par item (guard)
def watch_alerts(entity, watch_store, name_fn) -> list[Alert]:
    """Évalue les objets surveillés (durabilité/quantité) et signale les disparus.
    Les entrées correspondant à des objets disparus sont retirées du store."""
    # Regroupe les items courants par signature
    found: dict[str, list] = {}
    for inv in entity.inventories:
        for it in inv.items:
            found.setdefault(item_sig(it), []).append(it)

    out = []
    to_remove = []
    for sig, watch in list(watch_store.items().items()):
        name = name_fn(watch["sheet"]) if name_fn else watch["sheet"]
        q = watch.get("quality", 0)
        threshold = watch["threshold"]
        matches = found.get(sig)
        if not matches:
            out.append(Alert("unfound", f"{name} (Q{q}) : disparu",
                             "L'objet surveillé n'est plus présent."))
            to_remove.append(sig)
            continue
        if watch["kind"] == KIND_DURABILITY:
            hp = min(it.hp for it in matches)
            if hp < threshold:
                out.append(Alert("durability", f"{name} (Q{q}) : durabilité faible",
                                 f"Durabilité {hp} < seuil {threshold}"))
        else:
            qty = sum(it.stack for it in matches)
            if qty < threshold:
                out.append(Alert("quantity", f"{name} (Q{q}) : quantité faible",
                                 f"Quantité {qty} < seuil {threshold}"))
    for sig in to_remove:
        watch_store.remove_sig(sig)
    return out


# ---------------------------------------------------------------- Ventes
def sales_alerts(entity, sales_count: int, name_fn) -> list[Alert]:
    """Signale les items en vente qui expirent dans moins de `sales_count` heures."""
    out = []
    now = time.time()
    for inv in entity.inventories:
        if inv.key != "shop":
            continue
        for it in inv.items:
            if it.expires <= 0 or now >= it.expires:
                continue
            hours = (it.expires - now) / 3600.0
            if hours < sales_count:
                name = name_fn(it.sheet) if name_fn else it.sheet
                h = int(hours)
                m = int((hours - h) * 60)
                where = f" ({it.continent})" if it.continent else ""
                out.append(Alert("sales", f"{name} (Q{it.quality}) : vente bientôt expirée",
                                 f"Expire dans {h} h {m} min{where}"))
    return out


# ---------------------------------------------------------------- Saison
def season_alert(time_data: dict, season_count: int):
    """Alerte si la saison change dans moins de `season_count` heures."""
    minutes = time_data.get("minutes_to_next", 0)
    if minutes <= 0:
        return None
    hours = minutes / 60.0
    if hours >= season_count:
        return None
    h = int(hours)
    m = int((hours - h) * 60)
    return Alert(
        "season",
        f"Changement de saison dans {h} h {m} min",
        f"Saison actuelle : {time_data.get('season_name', '-')} "
        f"→ {time_data.get('next_season_name', '-')}",
    )


# ---------------------------------------------------------- Persistance
def load_snapshot(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def save_snapshot(path: str, snapshot: dict) -> None:
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(snapshot, fh)
    except Exception:
        pass
