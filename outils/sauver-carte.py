#!/usr/bin/env python3
"""Garde une copie de chaque version de la carte des membres.

    ./outils/sauver-carte.py            relève et sauvegarde
    ./outils/sauver-carte.py --liste    dit ce qui est déjà gardé, sans rien faire

**Pourquoi cet outil.** La carte est ouverte à l'édition : n'importe quel
visiteur peut déplacer un marqueur, ou tout effacer. uMap garde bien un
historique, mais c'est le sien — sa profondeur ne nous appartient pas, et une
suppression qui passerait inaperçue quelques semaines pourrait n'avoir plus
rien à restaurer. Ici, chaque version relevée est gardée pour de bon.

**Ce n'est pas un déclencheur, c'est un relevé.** uMap n'émet aucun signal
quand un membre enregistre : il n'y a ni notification ni webhook. On regarde
donc à intervalle régulier. Mais rien n'est perdu entre deux passages, parce
qu'on ne compare pas la carte à ce qu'on avait — on lit la **liste des
versions** qu'uMap tient lui-même, et l'on rapatrie toutes celles qui manquent.
Trois modifications dans le même quart d'heure font trois fichiers.

**Ce qui est demandé au réseau.** La liste des versions pèse quelques centaines
d'octets, et c'est tout ce qu'on récupère quand rien n'a bougé : les données ne
sont téléchargées que pour une version qu'on n'a pas.

Les calques ne sont pas écrits en dur : ils sont lus dans la page de la carte à
chaque passage. Un calque ajouté plus tard est donc sauvegardé sans que cet
outil ait à changer.
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

#: La carte, telle qu'elle s'ouvre dans un navigateur.
CARTE = "https://framacarte.org/fr/map/la-lune-eternelle_238251"

#: Son numero, celui que portent les adresses de donnees. Il est a la fin du
#: nom : `la-lune-eternelle_238251`.
NUMERO = CARTE.rsplit("_", 1)[1]

BASE = "https://framacarte.org"

#: Ou les copies s'empilent. Sous `~/.local/share`, comme les donnees des
#: autres outils maison : rien a installer, rien a nettoyer.
DOSSIER = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    "carte-lune-eternelle")

#: Framacarte sert une page differente aux clients qui ne se presentent pas.
#:
#: **En ASCII pur.** Les en-tetes HTTP se codent en latin-1 : un tiret
#: cadratin dans le nom du client fait echouer la requete avant meme qu'elle
#: parte, sur un `UnicodeEncodeError` qui ne parle pas de reseau du tout.
ENTETES = {"User-Agent": "sauver-carte (xiom.be) - sauvegarde de la carte"}


def lire(adresse: str) -> bytes:
    requete = urllib.request.Request(adresse, headers=ENTETES)
    with urllib.request.urlopen(requete, timeout=30) as reponse:
        return reponse.read()


def calques() -> list[tuple[str, str]]:
    """Les calques de la carte : `(identifiant, nom)`.

    Ils sont déposés dans la page sous forme de JSON échappé, dans l'attribut
    `data-settings`. On y prend le strict nécessaire plutôt que de démonter
    tout le bloc : sa forme change d'une version d'uMap à l'autre, et un
    identifiant suivi d'un nom, c'est ce qui ne bouge pas.
    """
    page = html.unescape(lire(CARTE).decode("utf-8", "replace"))
    debut = page.find('"datalayers"')
    if debut == -1:
        return []
    bloc = page[debut:debut + 20000]
    trouves = []
    for morceau in re.finditer(
            r'"name":\s*"([^"]*)".{0,400}?"id":\s*"([0-9a-f-]{36})"', bloc,
            re.S):
        nom, identifiant = morceau.group(1), morceau.group(2)
        if (identifiant, nom) not in trouves:
            trouves.append((identifiant, nom))
    return trouves


def versions(calque: str) -> list[dict]:
    """Ce qu'uMap garde encore de ce calque, du plus ancien au plus récent."""
    brut = lire(f"{BASE}/fr/datalayer/{NUMERO}/{calque}/versions/")
    listees = json.loads(brut.decode("utf-8")).get("versions", [])
    return sorted(listees, key=lambda v: int(v.get("at", 0)))


def horodatage(reference: str) -> str:
    """La référence d'uMap — des millisecondes — en une date qui se lit."""
    instant = datetime.fromtimestamp(int(reference) / 1000, timezone.utc)
    return instant.astimezone().strftime("%Y-%m-%d_%Hh%M")


def sauver(calque: str, nom: str) -> int:
    """Rapatrie les versions manquantes de ce calque. Rend leur nombre."""
    dossier = os.path.join(DOSSIER, calque)
    os.makedirs(dossier, exist_ok=True)
    # `dernier.geojson` est ecarte : c'est un raccourci vers la version la
    # plus recente, pas une version de plus, et son nom ne porte pas de
    # reference a decouper.
    deja = {f.rsplit("_", 1)[1].removesuffix(".geojson")
            for f in os.listdir(dossier)
            if f.endswith(".geojson") and "_" in f}

    neuves = 0
    for version in versions(calque):
        reference = str(version.get("ref", ""))
        if not reference or reference in deja:
            continue
        donnees = lire(f"{BASE}/fr/datalayer/{NUMERO}/{calque}/{reference}")
        fichier = os.path.join(
            dossier, f"{horodatage(reference)}_{reference}.geojson")
        with open(fichier, "wb") as sortie:
            sortie.write(donnees)
        # Le raccourci vers la derniere connue : c'est celle qu'on reimporte
        # dans uMap quand il faut reparer, sans avoir a lire les dates.
        with open(os.path.join(dossier, "dernier.geojson"), "wb") as sortie:
            sortie.write(donnees)
        points = len(json.loads(donnees).get("features", []))
        print(f"  + {os.path.basename(fichier)} — {points} point(s), "
              f"{len(donnees)} octets")
        neuves += 1
    return neuves


def lister() -> int:
    if not os.path.isdir(DOSSIER):
        print("Rien de sauvegardé pour l'instant.")
        return 0
    for calque in sorted(os.listdir(DOSSIER)):
        chemin = os.path.join(DOSSIER, calque)
        if not os.path.isdir(chemin):
            continue
        gardees = sorted(f for f in os.listdir(chemin)
                         if f.endswith(".geojson") and f != "dernier.geojson")
        print(f"{calque} : {len(gardees)} version(s)")
        for f in gardees[-5:]:
            print(f"  {f}")
    return 0


def main() -> int:
    if "--liste" in sys.argv:
        return lister()
    try:
        trouves = calques()
    except (urllib.error.URLError, OSError) as souci:
        # Le timer repassera : un reseau absent n'est pas une panne a signaler.
        print(f"Carte injoignable : {souci}", file=sys.stderr)
        return 1
    if not trouves:
        print("Aucun calque lu dans la page — la carte a-t-elle changé "
              "d'adresse ?", file=sys.stderr)
        return 1

    total = 0
    for identifiant, nom in trouves:
        try:
            neuves = sauver(identifiant, nom)
        except (urllib.error.URLError, OSError, ValueError) as souci:
            print(f"Calque « {nom} » : {souci}", file=sys.stderr)
            continue
        if neuves:
            print(f"Calque « {nom} » : {neuves} version(s) de plus.")
        total += neuves

    if not total:
        print("Rien de neuf.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
