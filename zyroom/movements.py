"""Journal des mouvements d'objets : ce qui est entré et sorti des inventaires.

Reprend la partie « mouvements » de la fenêtre d'alerte du Delphi
(UnitFormAlert.pas : atAdded / atRemoved / atModified), avec la même
distinction en trois types et le même horodatage à la seconde. La différence :
l'original vidait sa liste à la fermeture, ici les lignes sont conservées d'une
session à l'autre.

Les mouvements se déduisent de deux instantanés successifs
(`{clé_inventaire: {sheet|qualité: quantité}}`, cf. alerts.build_snapshot) :
l'API ne fournit aucun historique, seulement un état. On ne voit donc que ce
qui a changé entre deux synchronisations — deux mouvements qui s'annulent entre
elles passent inaperçus, exactement comme dans l'original.

Le fichier est en JSON Lines : une ligne = un mouvement, ajout par simple
append, et une ligne corrompue ne coûte que sa propre perte.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field

ADDED = "added"        # l'objet n'était pas là
REMOVED = "removed"    # l'objet n'y est plus
MODIFIED = "modified"  # la quantité a changé

#: Au-delà de cette taille, le journal est ramené à `_TRIM_TO` lignes.
_MAX_LINES = 20000
_TRIM_TO = 10000


@dataclass
class Movement:
    ts: float = 0.0          # horodatage Unix de la synchronisation
    inv_key: str = ""        # clé de l'inventaire, ex "chest4"
    inv_label: str = ""      # libellé au moment du mouvement, ex "Coffre 4 — ..."
    sheet: str = ""          # fiche de l'objet (le nom lisible est résolu à l'affichage)
    quality: int = 0
    kind: str = MODIFIED
    delta: int = 0           # quantité entrée (>0) ou sortie (<0)
    old: int = 0
    new: int = 0

    @property
    def when(self) -> str:
        """Date et heure lisibles, au format de l'original."""
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.ts))

    def as_dict(self) -> dict:
        return {"ts": self.ts, "inv": self.inv_key, "label": self.inv_label,
                "sheet": self.sheet, "q": self.quality, "kind": self.kind,
                "delta": self.delta, "old": self.old, "new": self.new}

    @classmethod
    def from_dict(cls, data: dict) -> "Movement":
        return cls(ts=float(data.get("ts", 0)), inv_key=data.get("inv", ""),
                   inv_label=data.get("label", ""), sheet=data.get("sheet", ""),
                   quality=int(data.get("q", 0)), kind=data.get("kind", MODIFIED),
                   delta=int(data.get("delta", 0)), old=int(data.get("old", 0)),
                   new=int(data.get("new", 0)))


def _labels(entity) -> dict[str, str]:
    return {inv.key: inv.label for inv in entity.inventories}


def diff(old: dict, new: dict, entity, ts: float | None = None) -> list[Movement]:
    """Mouvements entre deux instantanés, du plus récent inventaire au dernier.

    Seuls les inventaires présents dans le nouvel instantané sont examinés : un
    inventaire disparu (coffre masqué, animal vendu) ne doit pas faire croire
    que tout son contenu vient d'être retiré.
    """
    if ts is None:
        ts = time.time()
    labels = _labels(entity)
    out: list[Movement] = []

    for inv_key, new_counts in new.items():
        old_counts = old.get(inv_key, {})
        for sig in set(new_counts) | set(old_counts):
            before = old_counts.get(sig, 0)
            after = new_counts.get(sig, 0)
            if before == after:
                continue
            sheet, _, quality = sig.rpartition("|")
            if not sheet:                     # signature d'un format antérieur
                sheet, quality = sig, "0"
            if before == 0:
                kind = ADDED
            elif after == 0:
                kind = REMOVED
            else:
                kind = MODIFIED
            out.append(Movement(
                ts=ts, inv_key=inv_key, inv_label=labels.get(inv_key, inv_key),
                sheet=sheet, quality=int(quality) if quality.isdigit() else 0,
                kind=kind, delta=after - before, old=before, new=after,
            ))

    # Entrées d'abord, puis sorties, et par inventaire — ordre de lecture le
    # plus utile quand une synchronisation en rapporte beaucoup d'un coup.
    out.sort(key=lambda m: (m.inv_key, -m.delta))
    return out


def append(path: str, movements: list[Movement]) -> None:
    """Ajoute des mouvements au journal, en élaguant s'il a trop grossi."""
    if not movements:
        return
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            for mv in movements:
                fh.write(json.dumps(mv.as_dict(), ensure_ascii=False) + "\n")
        _trim(path)
    except OSError:
        pass          # un journal est un confort : ne jamais casser une synchro


def _trim(path: str) -> None:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        if len(lines) <= _MAX_LINES:
            return
        with open(path, "w", encoding="utf-8") as fh:
            fh.writelines(lines[-_TRIM_TO:])
    except OSError:
        pass


def load(path: str, limit: int | None = None) -> list[Movement]:
    """Relit le journal, du plus récent au plus ancien."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError:
        return []
    if limit:
        lines = lines[-limit:]
    out = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(Movement.from_dict(json.loads(line)))
        except (ValueError, TypeError):
            continue      # ligne tronquée par un arrêt brutal : on la saute
    # Tri stable sur l'horodatage seul : les synchros ressortent de la plus
    # récente à la plus ancienne, mais à l'intérieur de l'une d'elles l'ordre
    # d'écriture est conservé (entrées avant sorties, groupées par coffre).
    # Inverser les lignes du fichier retournerait aussi cet ordre-là.
    out.sort(key=lambda m: -m.ts)
    return out


def clear(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


def describe(mv: Movement, name_fn=None) -> str:
    """Ligne lisible, sur le modèle de l'original (RS_ALERT_ADDED/REMOVED/MODIFIED)."""
    name = name_fn(mv.sheet) if name_fn else mv.sheet
    quality = f" Q{mv.quality}" if mv.quality else ""
    if mv.kind == ADDED:
        what = f"l'objet {name}{quality} a été ajouté ({mv.new})"
    elif mv.kind == REMOVED:
        what = f"l'objet {name}{quality} a été retiré ({mv.old})"
    else:
        what = f"la quantité de l'objet {name}{quality} a changé ({mv.old} > {mv.new})"
    return f"{mv.when} | {mv.inv_label} : {what}"
