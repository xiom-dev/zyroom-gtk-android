"""Les avant-postes d'Atys : qui les tient, et le journal des prises.

Porté de `model/Outpost.kt`, `model/OutpostLevels.kt` et `data/OutpostStore.kt`
du portage Android, où cette logique est déjà couverte par des tests.

L'API ne dit d'un avant-poste que son identifiant — `fyros_outpost_04` — et la
guilde à qui il appartient. Ni le niveau, ni la production, ni les horaires
d'attaque : rien de tout cela n'est exposé. Le nom lisible, « Ferme de
Malmontagne », vient du pack du client, sous la clé `<code>.outpost`.

L'annuaire des guildes qui porte tout cela — `guilds.php` — **ne demande aucune
clé** : c'est la carte de tout le serveur, pas celle d'une guilde.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from xml.etree.ElementTree import fromstring


@dataclass(frozen=True)
class Outpost:
    """Un avant-poste et la guilde qui le tient."""

    code: str
    guild: str
    icon: str = ""          #: identifiant d'emblème, pour guild_icon.php

    @property
    def people(self) -> str:
        """« fyros », « matis », « tryker », « zorai »… — lu dans le code."""
        return self.code.split("_", 1)[0]

    @property
    def name_key(self) -> str:
        """La clé sous laquelle le pack range son nom."""
        return f"{self.code}.outpost"

    @property
    def level(self) -> int:
        """Son niveau, ou 0 s'il n'est pas connu. Voir NIVEAUX."""
        return NIVEAUX.get(self.code, 0)


#: Le niveau de chaque avant-poste.
#:
#: **L'API ne le donne pas.** Le niveau est pourtant une donnée fixe, qui ne
#: dépend ni du propriétaire ni du moment : le wiki de Ryzom l'énonce ainsi —
#: « la qualité des produits correspond au niveau de récolte maximal dans la
#: région où se situe l'avant-poste ». Un avant-poste ne change donc de niveau
#: que si le jeu change, et une table figée est ici la bonne réponse.
#:
#: Source : fr.wiki.ryzom.com/wiki/Avant-postes, recoupée avec
#: mymap.ryzom.eu.org — vingt-sept valeurs communes, aucun désaccord. Les
#: quatre `primes_outpost_*` n'y figurent pas : le pack les annonce « en test,
#: instable », et la table ne ment pas en leur inventant un niveau.
NIVEAUX: dict[str, int] = {
    "fyros_outpost_04": 200,
    "fyros_outpost_09": 150,
    "fyros_outpost_13": 100,
    "fyros_outpost_14": 50,
    "fyros_outpost_25": 200,
    "fyros_outpost_27": 250,
    "fyros_outpost_28": 250,
    "matis_outpost_03": 200,
    "matis_outpost_07": 100,
    "matis_outpost_15": 50,
    "matis_outpost_17": 150,
    "matis_outpost_24": 250,
    "matis_outpost_27": 250,
    "matis_outpost_30": 200,
    "tryker_outpost_06": 50,
    "tryker_outpost_10": 150,
    "tryker_outpost_16": 200,
    "tryker_outpost_22": 200,
    "tryker_outpost_24": 100,
    "tryker_outpost_29": 250,
    "tryker_outpost_31": 250,
    "zorai_outpost_02": 200,
    "zorai_outpost_08": 50,
    "zorai_outpost_10": 100,
    "zorai_outpost_15": 250,
    "zorai_outpost_16": 250,
    "zorai_outpost_22": 150,
    "zorai_outpost_29": 200,
}


# --------------------------------------------------------------- Lecture

def parse_outposts(xml_bytes: bytes) -> list[Outpost]:
    """L'annuaire des guildes → la liste des avant-postes tenus.

    `guilds.php` rend les 2 420 guildes du serveur, chacune avec son emblème et
    les avant-postes qu'elle tient. Les guildes sans nom sont écartées : le flux
    en contient quelques-unes, vestiges de guildes dissoutes.
    """
    root = fromstring(xml_bytes)
    trouves: list[Outpost] = []
    for guilde in root.iter("guild"):
        nom = (guilde.findtext("name") or "").strip()
        if not nom:
            continue
        embleme = (guilde.findtext("icon") or "").strip()
        for noeud in guilde.iter("outpost"):
            code = (noeud.text or "").strip()
            if code:
                trouves.append(Outpost(code=code, guild=nom, icon=embleme))
    return trouves


# ------------------------------------------------- Journal des prises

@dataclass(frozen=True)
class Change:
    """Un changement de main.

    `frm` et `to` sont vides quand l'avant-poste n'appartenait, ou n'appartient
    plus, à personne."""

    at: int                 #: secondes Unix, comme les autres journaux
    outpost: str
    frm: str
    to: str

    @property
    def taken(self) -> bool:
        return not self.frm

    @property
    def lost(self) -> bool:
        return not self.to


def diff(avant: dict[str, str], apres: dict[str, str]) -> list[Change]:
    """Ce qui a changé de main entre deux relevés.

    Les deux états sont réunis : un avant-poste rendu à personne disparaît du
    nouvel état, et son abandon serait sinon invisible."""
    maintenant = int(time.time())
    changements = []
    for code in sorted(set(avant) | set(apres)):
        depuis, vers = avant.get(code, ""), apres.get(code, "")
        if depuis != vers:
            changements.append(Change(maintenant, code, depuis, vers))
    return changements


class OutpostStore:
    """Le journal des prises et des pertes, sur tout Atys.

    Même principe que le journal des mouvements, et pour la même raison : l'API
    ne rend qu'un état, jamais une histoire. Deux relevés successifs comparés
    donnent les changements ; ce qui se passe entre les deux — un avant-poste
    pris puis repris le lendemain — se voit comme un seul changement, et deux
    mouvements qui s'annulent ne se voient pas du tout.

    Un seul jeu de fichiers pour tout le serveur, et non un par entité : la
    carte des avant-postes ne dépend d'aucune clé d'API.
    """

    def __init__(self, dossier: str) -> None:
        self._dir = dossier

    def _journal(self) -> str:
        return os.path.join(self._dir, "outposts.jsonl")

    def _etat(self) -> str:
        return os.path.join(self._dir, "outposts-etat.json")

    def jamais_releve(self) -> bool:
        """Vrai tant qu'aucun relevé n'a été fait : le journal ne peut rien dire."""
        return not os.path.isfile(self._etat())

    def record(self, carte: list[Outpost]) -> list[Change]:
        """Confronte la carte au dernier état connu et journalise les prises.

        Au tout premier relevé il n'y a rien à comparer : on enregistre sans
        rien journaliser, sinon les vingt-neuf avant-postes passeraient pour
        autant de prises le jour de l'installation.
        """
        apres = {o.code: o.guild for o in carte}
        avant = self._lire_etat()
        changements = [] if avant is None else diff(avant, apres)
        if changements:
            self._ajouter(changements)
        self._ecrire_etat(apres)
        return changements

    def history(self) -> list[Change]:
        """Le journal, du plus récent au plus ancien."""
        chemin = self._journal()
        if not os.path.isfile(chemin):
            return []
        lignes = []
        try:
            with open(chemin, encoding="utf-8") as fh:
                for ligne in fh:
                    if not ligne.strip():
                        continue
                    try:
                        o = json.loads(ligne)
                    except ValueError:
                        continue
                    lignes.append(Change(int(o.get("at", 0)),
                                         o.get("outpost", ""),
                                         o.get("from", ""), o.get("to", "")))
        except OSError:
            return []
        # Tri stable sur le seul horodatage, comme le journal des mouvements :
        # lire le fichier à l'envers retournerait aussi l'ordre interne d'un
        # même relevé.
        lignes.sort(key=lambda c: c.at, reverse=True)
        return lignes

    def clear(self) -> None:
        try:
            os.remove(self._journal())
        except OSError:
            pass

    def _lire_etat(self) -> dict[str, str] | None:
        try:
            with open(self._etat(), encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return None

    def _ecrire_etat(self, carte: dict[str, str]) -> None:
        try:
            os.makedirs(self._dir, exist_ok=True)
            with open(self._etat(), "w", encoding="utf-8") as fh:
                json.dump(carte, fh)
        except OSError:
            pass

    def _ajouter(self, changements: list[Change]) -> None:
        try:
            os.makedirs(self._dir, exist_ok=True)
            with open(self._journal(), "a", encoding="utf-8") as fh:
                for c in changements:
                    fh.write(json.dumps({"at": c.at, "outpost": c.outpost,
                                         "from": c.frm, "to": c.to}) + "\n")
        except OSError:
            pass
