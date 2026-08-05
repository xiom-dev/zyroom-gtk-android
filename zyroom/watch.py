"""Objets surveillés par l'utilisateur (durabilité d'un équipement / quantité
d'une matière). Équivalent du guard.dat d'origine.

Chaque entité (perso/guilde) a sa liste, persistée en JSON. Une entrée est
identifiée par la signature de l'item (sheet|qualité) et porte un seuil :
  - équipement  -> alerte si la durabilité (hp) descend sous le seuil ;
  - matière     -> alerte si la quantité descend sous le seuil.
"""
from __future__ import annotations

import json
import os

from .models import ItemInfo, ItemType, item_sig

KIND_DURABILITY = "durability"
KIND_QUANTITY = "quantity"


def watch_kind(item: ItemInfo) -> str:
    """Type de surveillance déduit du type d'item (comme le Delphi)."""
    return KIND_DURABILITY if item.item_type == ItemType.EQUIPMENT else KIND_QUANTITY


class WatchStore:
    def __init__(self, path: str) -> None:
        self._path = path
        self._data: dict[str, dict] = {}
        try:
            with open(path, "r", encoding="utf-8") as fh:
                self._data = json.load(fh)
        except Exception:
            self._data = {}

    def items(self) -> dict[str, dict]:
        return self._data

    def is_watched(self, item: ItemInfo) -> bool:
        return item_sig(item) in self._data

    def add(self, item: ItemInfo, threshold: int) -> None:
        self._data[item_sig(item)] = {
            "sheet": item.sheet,
            "quality": item.quality,
            "threshold": int(threshold),
            "kind": watch_kind(item),
        }
        self._flush()

    def remove(self, item: ItemInfo) -> None:
        if self._data.pop(item_sig(item), None) is not None:
            self._flush()

    def remove_sig(self, sig: str) -> None:
        if self._data.pop(sig, None) is not None:
            self._flush()

    def _flush(self) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh)
        except Exception:
            pass
