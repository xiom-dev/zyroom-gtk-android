"""Chargement de sheetid.csv : identifiant numérique '#123' -> nom de fiche.

Équivalent du TStringList FSheetId (UnitRyzom.pas). Le fichier contient des
lignes `#<id>=<nom>` ; GetSheetName ajoute l'extension '.sitem'.
"""
from __future__ import annotations

import os


class SheetDb:
    def __init__(self) -> None:
        self._map: dict[str, str] = {}

    def load(self, path: str) -> bool:
        """Charge le CSV s'il existe. Renvoie True si chargé."""
        if not os.path.isfile(path):
            return False
        mapping: dict[str, str] = {}
        # Le fichier est en Latin-1 (ISO-8859) dans la distribution d'origine.
        with open(path, "r", encoding="latin-1") as fh:
            for line in fh:
                line = line.rstrip("\r\n")
                if not line or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                mapping[key] = value
        self._map = mapping
        return True

    def name(self, sheet_id: str) -> str:
        """'#123' -> 'xxx.sitem' (ou l'identifiant tel quel si introuvable)."""
        value = self._map.get(sheet_id)
        return f"{value}.sitem" if value else sheet_id

    def __len__(self) -> int:
        return len(self._map)
