"""Alertes : surveillance du volume et des mouvements d'objets.

Reproduit deux des surveillances de zyRoom d'origine :
  - **Volume** : une pièce / un contenant dépasse un seuil de remplissage (%).
  - **Mouvement** : des objets sont apparus ou ont disparu depuis la dernière
    synchronisation (comparaison à un instantané, façon watch.dat).

Les surveillances par item (durabilité d'un équipement, quantité d'une matière)
viendront ensuite ; elles nécessitent une liste d'objets surveillés par l'utilisateur.
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
    kind: str          # 'volume' | 'movement' | 'durability' | 'quantity' | 'unfound' | 'sales' | 'season'
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


# --------------------------------------------------------------- Mouvements
def build_snapshot(entity) -> dict:
    """Instantané {clé_inventaire: {signature: quantité}}.
    signature = 'sheet|qualité' ; quantité = somme des piles."""
    snap: dict[str, dict[str, int]] = {}
    for inv in entity.inventories:
        counts: dict[str, int] = {}
        for it in inv.items:
            sig = item_sig(it)
            counts[sig] = counts.get(sig, 0) + max(it.stack, 1)
        snap[inv.key] = counts
    return snap


def _label(inv_key: str, entity) -> str:
    for inv in entity.inventories:
        if inv.key == inv_key:
            return inv.label
    return inv_key


def diff_snapshots(old: dict, new: dict, entity, name_fn) -> list[Alert]:
    """Compare deux instantanés et renvoie les mouvements détectés."""
    out = []
    for inv_key, new_counts in new.items():
        old_counts = old.get(inv_key, {})
        sigs = set(new_counts) | set(old_counts)
        changes = []
        for sig in sigs:
            delta = new_counts.get(sig, 0) - old_counts.get(sig, 0)
            if delta != 0:
                sheet = sig.rsplit("|", 1)[0]
                name = name_fn(sheet) if name_fn else sheet
                changes.append((delta, name))
        if changes:
            # tri : ajouts d'abord (delta desc)
            changes.sort(key=lambda c: -c[0])
            lines = [f"{'+' if d > 0 else ''}{d}  {n}" for d, n in changes]
            out.append(Alert(
                "movement",
                f"{_label(inv_key, entity)} : {len(changes)} mouvement(s)",
                "\n".join(lines),
            ))
    return out


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
