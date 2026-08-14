#!/usr/bin/env python3
"""Fabrique les tables de pop des deux portages : ce qui sort, et par quel temps.

Deux sources, et **plus le classeur de la guilde**.

* *quoi, où, quand dans l'année* : `armory.SUPREMES`, le relevé de Ryzom
  Armory, saison par saison et zone par zone des Primes ;
* *par quel temps* : la fourchette d'humidité de chaque gisement, relevée au
  tracker d'atys.us par `outils/humidites.py`.

Le jeu range l'humidité en quatre bandes, et **chaque gisement en occupe
exactement deux** :

    0 – 16,6 %     Excellente      (BEST)
    16,7 – 49,9 %  Bonne           (GOOD)
    50 – 83,3 %    Mauvaise        (BAD)
    83,4 – 100 %   Exécrable       (WORST)

Sec vaut mieux qu'humide — l'inverse de ce qu'on croirait. Mesuré sur l'API du
jeu, quarante et un cycles sans une exception.

**Pourquoi le classeur a été abandonné.** Il donnait ces conditions de mémoire,
au fil des sorties des joueurs, et il était à la fois incomplet et faux : sur
les quarante-six matières qu'il cite, **une seule** s'accordait avec la
fourchette d'humidité du jeu. Il donnait souvent trois conditions là où le jeu
en donne toujours deux.

**Ce que le tracker ne peut pas dire.** Il ne connaît qu'une des quatre zones
des Primes — « Under Spring », nos Sources Interdites. Le couple saison × zone
vient donc d'Armory. Les deux sources ont été confrontées là où elles se
recoupent : pour les Sources Interdites en été, **trente-cinq matières sur
trente-cinq**, famille par famille, sans un écart.

    python3 outils/table_pop.py

À relancer après `outils/humidites.py`, ou quand Ryzom change ses matières.
"""
import collections
import os
import json
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_ANDROID = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEPOT = os.path.dirname(_ANDROID)
sys.path.insert(0, os.path.join(_DEPOT, "zyroom-gtk"))

from table_gisements import (FAMILLE_CORRIGEE, FAMILLES_FR,        # noqa: E402
                             MATIERES_FR, normalise)
from zyroom import armory                                          # noqa: E402

HUMIDITES = os.path.join(_DEPOT, "donnees", "humidites-gisements.json")

#: Les quatre bandes du jeu, et la condition de gisement qu'elles portent.
#: L'ordre est celui de l'humidité croissante ; il ne suit donc pas celui des
#: conditions, puisque c'est le temps sec qui vaut le mieux.
BANDES = ((0.0, 16.6, "BEST"), (16.7, 49.9, "GOOD"),
          (50.0, 83.3, "BAD"), (83.4, 100.0, "WORST"))

#: L'ordre d'affichage, du pire au meilleur — celui des colonnes de l'écran.
CONDITIONS = ("Worst", "Bad", "Good", "Best")

FAMILLES = ("Ambres", "Graines", "Fibres", "Résine", "Huile", "Sève",
            "Carapace", "Écorce", "Bois", "Boucles")

ZONES = ("Sources Interdites", "Terre de la Continuité",
         "Cité Engloutie", "Profondeurs Interdites")

#: Zone des Primes → continent dont on lit la météo. Les quatre zones ne
#: partagent que deux séries : vérifié sur quarante cycles.
CONTINENTS = {
    "Sources Interdites": "sources",
    "Terre de la Continuité": "terre",
    "Cité Engloutie": "terre",
    "Profondeurs Interdites": "terre",
}


def fourchettes() -> dict:
    with open(HUMIDITES, encoding="utf-8") as fh:
        return json.load(fh)["humidites"]


def conditions_de(humidites: dict, famille: str, brute: str) -> tuple:
    """Les conditions où cette matière sort, d'après sa fourchette d'humidité.

    Rend aussi le nom propre : le relevé d'Armory écrit « Scrath » ou
    « Redhot » là où l'écran doit lire « Scratch » et « Ardente ».
    """
    nom = normalise(brute)
    vraie = FAMILLE_CORRIGEE.get(nom, famille)
    cle = f"supreme|{FAMILLES_FR.get(vraie)}|{MATIERES_FR.get(nom)}"
    plages = humidites.get(cle)
    if not plages:
        return nom, None
    dedans = tuple(c for bas, haut, c in BANDES
                   if any(p0 <= bas and haut <= p1 for p0, p1 in plages))
    return nom, dedans


def table() -> dict:
    """{saison: {zone: {condition: {famille: [matières]}}}}."""
    humidites = fourchettes()
    tout, orphelines = collections.OrderedDict(), []
    for saison, zones in armory.SUPREMES.items():
        par_zone = collections.OrderedDict()
        for zone in ZONES:
            groupes = zones.get(zone, {})
            par_condition = collections.defaultdict(
                lambda: collections.defaultdict(list))
            for famille in FAMILLES:
                for brute in groupes.get(famille, []):
                    nom, conditions = conditions_de(humidites, famille, brute)
                    if conditions is None:
                        orphelines.append(f"{famille} / {brute}")
                        continue
                    for condition in conditions:
                        par_condition[condition][famille].append(nom)
            if par_condition:
                par_zone[zone] = {
                    c.upper(): {f: sorted(set(ms))
                                for f, ms in sorted(par_condition[c.upper()].items(),
                                                    key=lambda p: FAMILLES.index(p[0]))}
                    for c in CONDITIONS if c.upper() in par_condition}
        tout[saison] = par_zone
    if orphelines:
        print("Des matières n'ont pas de fourchette d'humidité :", file=sys.stderr)
        for ligne in sorted(set(orphelines)):
            print("  " + ligne, file=sys.stderr)
        raise SystemExit("relance outils/humidites.py, ou complète MATIERES_FR")
    return tout


ENTETE = (
    "Ce qui peut apparaître, par saison, par zone et par condition météo.",
    "",
    "Deux sources : le relevé de Ryzom Armory pour le couple saison × zone, et",
    "la fourchette d'humidité de chaque gisement, relevée au tracker d'atys.us,",
    "pour la condition. Le jeu range l'humidité en quatre bandes et chaque",
    "gisement en occupe exactement deux — sec vaut mieux qu'humide.",
    "",
    "La table est donc **complète** : chaque matière de chaque zone y figure",
    "sous ses deux conditions. Le classeur de la guilde, qu'elle remplace,",
    "était rempli de mémoire et ne s'accordait avec le jeu que sur une matière",
    "sur quarante-six.",
)


def kotlin(tout: dict) -> str:
    lignes = ['package net.ryzom.zyroom.model', '',
              '// Fichier produit par outils/table_pop.py — ne pas modifier à la main.',
              '', '/**']
    lignes += [(" * " + l).rstrip() for l in ENTETE]
    lignes += [' */',
               'val POP: Map<String, Map<String, Map<String, Map<String, List<String>>>>> = mapOf(']
    for saison, zones in tout.items():
        lignes.append(f'    "{saison}" to mapOf(')
        for zone, conds in zones.items():
            lignes.append(f'        "{zone}" to mapOf(')
            for cond in CONDITIONS:
                if cond.upper() not in conds:
                    continue
                lignes.append(f'            "{cond.upper()}" to mapOf(')
                for famille, mats in conds[cond.upper()].items():
                    liste = ", ".join(f'"{m}"' for m in mats)
                    lignes.append(f'                "{famille}" to listOf({liste}),')
                lignes.append('            ),')
            lignes.append('        ),')
        lignes.append('    ),')
    lignes.append(')')
    lignes += ['', '/** Zone du relevé -> continent interrogé pour la météo. */',
               'val CONTINENT_DE_ZONE: Map<String, String> = mapOf(']
    for zone, cont in CONTINENTS.items():
        lignes.append(f'    "{zone}" to "{cont}",')
    lignes.append(')')
    return "\n".join(lignes) + "\n"


def python(tout: dict) -> str:
    """La même table, pour le portage GTK.

    Deux fichiers produits d'un seul geste, comme pour `table_armory.py` : une
    table recopiée à la main d'un langage à l'autre finit toujours par
    diverger, et personne ne s'en aperçoit avant de comparer les deux
    applications côte à côte."""
    lignes = ['"""' + ENTETE[0]]
    lignes += list(ENTETE[1:])
    lignes += ['',
               'Fichier produit par ../zyroom-android/outils/table_pop.py — ne pas',
               'modifier à la main.',
               '"""', '',
               '#: {saison: {zone: {condition: {famille: [matières]}}}}',
               'POP = {']
    for saison, zones in tout.items():
        lignes.append(f'    "{saison}": {{')
        for zone, conds in zones.items():
            lignes.append(f'        "{zone}": {{')
            for cond in CONDITIONS:
                if cond.upper() not in conds:
                    continue
                lignes.append(f'            "{cond.upper()}": {{')
                for famille, mats in conds[cond.upper()].items():
                    liste = ", ".join(f'"{m}"' for m in mats)
                    lignes.append(f'                "{famille}": [{liste}],')
                lignes.append('            },')
            lignes.append('        },')
        lignes.append('    },')
    lignes += ['}', '',
               '#: Zone du relevé -> continent interrogé pour la météo.',
               'CONTINENT_DE_ZONE = {']
    for zone, cont in CONTINENTS.items():
        lignes.append(f'    "{zone}": "{cont}",')
    lignes.append('}')
    return "\n".join(lignes) + "\n"


def main() -> int:
    tout = table()
    for saison, zones in tout.items():
        total = sum(len(m) for z in zones.values() for c in z.values()
                    for m in c.values())
        print(f"{saison:10} {len(zones)} zones, {total:3} entrées")
    for cible, contenu in (
        (os.path.join(_ANDROID,
                      "app/src/main/kotlin/net/ryzom/zyroom/model/PopTable.kt"),
         kotlin(tout)),
        (os.path.join(_DEPOT, "zyroom-gtk/zyroom/pop.py"), python(tout)),
    ):
        with open(cible, "w", encoding="utf-8") as fh:
            fh.write(contenu)
        print("→", cible)
    return 0


if __name__ == "__main__":
    sys.exit(main())
