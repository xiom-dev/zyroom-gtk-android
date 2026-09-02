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

from .noms_avant_postes import NOMS_AVANT_POSTES

import json
import re
import os
import struct


#: Codes de l'arbre des compétences : « sf », « sfm », « scahbem »… Le flux
#: personnage ne nomme les compétences que par eux, et c'est le pack qui porte
#: leur nom français. La règle retient un peu plus large que l'arbre — quatre
#: clés comme « sapalchemy » passent aussi —, sans conséquence : on ne cherche
#: jamais qu'un code venu du flux, et une clé du pack n'a qu'une valeur.
_SKILL_CODE = re.compile(r"^s[a-z0-9]{1,9}$")


def _utile(key: str) -> bool:
    """Ce que l'application sait nommer : items, avant-postes, compétences, sorts.

    Le pack en contient vingt-six mille, dialogues et missions compris.

    Les **briques** (`.sbrick`) sont les morceaux d'un sort : le flux personnage
    ne donne d'un enchantement que leurs identifiants — `bmpa01.sbrick`,
    `bmoetea04.sbrick` —, et c'est le pack qui les rend lisibles : « Missile
    Atysien », « Dégât d'Électricité ». Elles sont quatre mille et pèsent une
    centaine de kilo-octets de plus dans le cache JSON, pour la seule chose qui
    dise ce qu'une arme enchantée fait vraiment."""
    return (key.endswith(".sitem") or key.endswith(".outpost")
            or key.endswith(".sbrick") or bool(_SKILL_CODE.match(key)))


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
        cle_brute = data[i + 4:i + 4 + klen]
        # Une clé du pack est un identifiant : ni espace, ni octet accentué, ni
        # caractère de contrôle. Sans cette vérification, une suite d'octets
        # quelconque tombant au bon endroit passait pour un enregistrement, et
        # le vrai qui commençait à l'intérieur était sauté — le parcours
        # cherchant octet par octet quand un enregistrement ne se présente pas.
        if not all(0x21 <= b <= 0x7E for b in cle_brute):
            i += 1
            continue
        try:
            key = cle_brute.decode("latin-1")
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
        """Nom lisible de la fiche, ou l'identifiant lui-même si inconnu.

        Le pack du client passe en premier : c'est la source du jeu, et elle
        suit ses mises à jour. À son défaut, les avant-postes ont une table
        embarquée — sans elle, une installation sans pack affiche
        « fyros_outpost_04 » là où il faut lire « Ferme de Malmontagne ».
        """
        connu = self._map.get(sheet)
        if connu is not None:
            return connu
        if sheet.endswith(".outpost"):
            return NOMS_AVANT_POSTES.get(sheet[:-len(".outpost")], sheet)
        return sheet

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
            # Le numéro de format en tête : le cache doit être refait quand les
            # règles d'extraction changent, et pas seulement quand le pack
            # change. Sans lui, la correction du lecteur n'aurait servi à
            # personne — chacun aurait gardé la table incomplète tirée du même
            # fichier. À incrémenter à chaque changement de _parse_pack ou du
            # filtre ci-dessous.
            signature = f"v4:{int(stat.st_mtime)}:{stat.st_size}"
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
                         if _utile(k)}
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
