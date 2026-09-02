"""Caractéristiques des matières de craft (category.csv).

Portage de la lecture de FCatStrings (UnitRyzom.pas). Chaque matière occupe
DEUX lignes consécutives (catégorie 1 puis catégorie 2), la clé étant les 5
premiers caractères du nom de fiche. Format d'une valeur :
  `07 168 012025033...`
   ^^ catégorie (index _MAT_CATEGORY)
      ^^^ 3 chiffres de couleur (basique/fin, choix/xl/sup, primes)
          suite = paires (index_spec sur 2 chiffres)(niveau 1-5)
"""
from __future__ import annotations

import os
import re

from .models import ItemInfo

_SPEC_RE = re.compile(r"(\d\d)(\d)")


class CategoryDb:
    def __init__(self) -> None:
        self._values: list[str] = []          # valeurs dans l'ordre du fichier
        self._index: dict[str, int] = {}       # préfixe -> index de la 1re ligne

    def load(self, path: str) -> bool:
        if not os.path.isfile(path):
            return False
        self._values = []
        self._index = {}
        with open(path, "r", encoding="latin-1") as fh:
            for line in fh:
                line = line.rstrip("\r\n")
                if "=" not in line:
                    continue
                key, _, val = line.partition("=")
                if key not in self._index:
                    self._index[key] = len(self._values)
                self._values.append(val)
        return bool(self._values)

    @staticmethod
    def _specs(value: str) -> list[tuple[int, int]]:
        return [(int(m.group(1)), int(m.group(2))) for m in _SPEC_RE.finditer(value[5:])]

    def fill(self, item: ItemInfo) -> None:
        """Remplit les champs mat_* de l'item si sa fiche est répertoriée."""
        idx = self._index.get(item.sheet[:5])
        if idx is None or idx >= len(self._values):
            return
        val1 = self._values[idx]
        if len(val1) < 5:
            return
        item.mat_category1 = int(val1[0:2])
        item.mat_colors = [int(val1[2]), int(val1[3]), int(val1[4])]
        item.mat_specs1 = self._specs(val1)
        # catégorie 2 = ligne suivante (sauf larve de Kitin m0312)
        if not item.sheet.startswith("m0312") and idx + 1 < len(self._values):
            val2 = self._values[idx + 1]
            if len(val2) >= 5:
                item.mat_category2 = int(val2[0:2])
                if item.mat_category2 > 0:
                    item.mat_specs2 = self._specs(val2)
