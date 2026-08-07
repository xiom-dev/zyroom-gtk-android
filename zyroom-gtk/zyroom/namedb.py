"""Noms d'items lisibles depuis le fichier `string_client.pack` de Ryzom.

Deux formats se rencontrent, tous deux en-têtés « STR_PACK ». Un enregistrement
vaut keylen(4 o, petit-boutiste) + clé(latin-1) + un octet séparateur +
vallen(4 o) + valeur, et c'est le séparateur qui dit comment lire la valeur :

    0x01  valeur en UTF-16LE, `vallen` comptant des unités (donc 2×vallen octets)
    0x02  valeur en UTF-8, `vallen` comptant des octets

Le 0x02 est ce qu'écrivent les clients récents ; le 0x01 est l'ancien, celui que
lisait zyRoom 6. Un pack au format récent lu comme l'ancien ne rend rien du
tout — d'où la panne où tous les items retombaient sur leur identifiant.

Le pack fait partie de l'installation du jeu (dossier de Ryzom). Chaque joueur
peut y pointer via les réglages ; en son absence, on retombe sur l'identifiant
technique de la fiche. Le résultat est mis en cache (JSON) pour un chargement
quasi instantané aux lancements suivants.
"""
from __future__ import annotations

import json
import os
import struct


def _parse_pack(data: bytes) -> dict[str, str]:
    out: dict[str, str] = {}
    n = len(data)
    i = 0
    while i < n - 8:
        # padding éventuel entre enregistrements
        while i < n and data[i] == 0:
            i += 1
        if i >= n - 8:
            break
        klen = struct.unpack_from("<I", data, i)[0]
        if not (1 <= klen <= 200) or i + 4 + klen + 1 > n:
            i += 1
            continue
        separator = data[i + 4 + klen]
        if separator not in (0x01, 0x02):
            i += 1
            continue
        # Largeur d'un caractère de la valeur : deux octets en UTF-16, un en UTF-8.
        width = 2 if separator == 0x01 else 1
        vpos = i + 4 + klen + 1
        if vpos + 4 > n:
            break
        vlen = struct.unpack_from("<I", data, vpos)[0]
        if vlen > 100000 or vpos + 4 + width * vlen > n:
            i += 1
            continue
        try:
            key = data[i + 4:i + 4 + klen].decode("latin-1")
            raw = data[vpos + 4:vpos + 4 + width * vlen]
            val = raw.decode("utf-16-le") if width == 2 else raw.decode("utf-8")
        except Exception:
            i += 1
            continue
        out[key] = val
        i = vpos + 4 + width * vlen
    return out


class NameDb:
    """Table fiche -> nom lisible. Vide tant qu'aucun pack n'est chargé."""

    def __init__(self, cache_path: str | None = None) -> None:
        self._map: dict[str, str] = {}
        self._cache_path = cache_path

    @property
    def loaded(self) -> bool:
        return bool(self._map)

    def name(self, sheet: str) -> str:
        """Nom lisible de la fiche, ou l'identifiant lui-même si inconnu."""
        return self._map.get(sheet, sheet)

    def load_cache(self) -> bool:
        """Reprend les noms déjà extraits, sans le pack.

        Le pack appartient à l'installation du jeu : il peut être déplacé ou
        effacé après coup. Les noms qu'on en a tirés, eux, restent bons — sans
        ce repli, déplacer le fichier suffisait à faire réapparaître partout
        les identifiants de fiches."""
        if not self._cache_path or not os.path.isfile(self._cache_path):
            return False
        try:
            with open(self._cache_path, "r", encoding="utf-8") as fh:
                self._map = json.load(fh).get("names", {})
        except Exception:
            return False
        return bool(self._map)

    def load(self, pack_path: str) -> bool:
        """Charge les noms depuis le pack (via cache JSON si à jour).
        Renvoie True si des noms ont été chargés."""
        if not pack_path or not os.path.isfile(pack_path):
            return False
        try:
            stat = os.stat(pack_path)
            signature = f"{int(stat.st_mtime)}:{stat.st_size}"
            if self._cache_path and os.path.isfile(self._cache_path):
                with open(self._cache_path, "r", encoding="utf-8") as fh:
                    cached = json.load(fh)
                # Un cache vide ne vaut rien : le relire serait se priver du
                # pack sans raison. On le traite comme absent.
                if cached.get("signature") == signature and cached.get("names"):
                    self._map = cached["names"]
                    return True
            with open(pack_path, "rb") as fh:
                names = {k: v for k, v in _parse_pack(fh.read()).items()
                         if k.endswith(".sitem")}
            if not names:
                # Pack illisible : format inconnu, fichier tronqué. Ne rien
                # écraser — ni les noms en place, ni le cache, qui sont bons.
                return False
            self._map = names
            if self._cache_path:
                with open(self._cache_path, "w", encoding="utf-8") as fh:
                    json.dump({"signature": signature, "names": self._map}, fh)
            return True
        except Exception:
            return False
