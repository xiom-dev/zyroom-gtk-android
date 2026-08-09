#!/usr/bin/env python3
"""Fabrique `model/PopTable.kt` à partir du classeur de la guilde.

Le classeur recense, par saison, par zone des Primes et par condition
météo, quelles sources de matières premières peuvent apparaître. C'est le
travail des joueurs de La Lune Eternelle, et la seule source connue pour
cette correspondance : les sites publics disent *quelles* matières sont
suprêmes, jamais *quand* elles sortent.

    python3 outils/table_pop.py            # va chercher le classeur en ligne
    python3 outils/table_pop.py dossier/   # relit des CSV déjà téléchargés

À relancer quand la guilde complète le tableau. Le classeur est incomplet
par construction — son premier onglet le dit : « le but n'est pas de camper
dans les primes pour le remplir, mais de compléter petit à petit ».
"""
import csv
import collections
import io
import os
import sys
import urllib.request

CLASSEUR = "1PatNA8_AjOvrNLSaNffH9ca7rRggWclvCe0oMHjPLA0"
ONGLETS = {                     # saison -> gid, dans l'ordre de l'API (0..3)
    "PRINTEMPS": 1931271042,
    "ETE": 1578394161,
    "AUTOMNE": 620712349,
    "HIVER": 1495467871,
}
CONDITIONS = ("Worst", "Bad", "Good", "Best")

#: Zone du classeur -> continent de l'API météo. Trois des quatre zones
#: partagent le continent « terre » : elles ont donc, au même instant, la
#: même météo, mais pas les mêmes gisements.
CONTINENTS = {
    "Sources Interdites": "sources",
    "Terre de la Continuité": "terre",
    "Cité Engloutie": "terre",
    "Profondeurs Interdites": "terre",
}

FAMILLES = ("Ambres", "Graines", "Fibres", "Résine", "Huile", "Sève",
            "Carapace", "Écorce", "Bois", "Boucles")


def lire(texte: str) -> dict:
    """Un onglet de saison -> {zone: {condition: {famille: [matières]}}}."""
    table, zone, condition, familles = collections.OrderedDict(), None, None, []
    for ligne in csv.reader(io.StringIO(texte)):
        ligne = ligne + [""] * (13 - len(ligne))
        entete = [c.strip() for c in ligne[3:13]]
        if entete[:1] == [FAMILLES[0]]:
            familles = entete
            continue
        libelle = ligne[1].strip()
        if libelle:
            # Les intitulés hors zones connues sont des titres de section
            # (« Été changement de saison ») : on les ignore plutôt que de
            # les prendre pour des lieux.
            zone = libelle if libelle in CONTINENTS else None
            condition = None
        if ligne[2].strip() in CONDITIONS:
            condition = ligne[2].strip()
        if not (zone and condition and familles):
            continue
        for i, cellule in enumerate(ligne[3:13]):
            nom = cellule.strip()
            if not nom or i >= len(familles):
                continue
            matieres = (table.setdefault(zone, collections.OrderedDict())
                             .setdefault(condition, collections.OrderedDict())
                             .setdefault(familles[i], []))
            if nom not in matieres:
                matieres.append(nom)
    return table


def source(saison: str, gid: int, dossier: str | None) -> str:
    if dossier:
        with open(os.path.join(dossier, f"saison-{saison.lower()}.csv"),
                  encoding="utf-8") as fh:
            return fh.read()
    url = (f"https://docs.google.com/spreadsheets/d/{CLASSEUR}"
           f"/export?format=csv&gid={gid}")
    with urllib.request.urlopen(url, timeout=60) as reponse:
        return reponse.read().decode("utf-8")


def kotlin(tout: dict) -> str:
    lignes = ['package net.ryzom.zyroom.model', '',
              '// Fichier produit par outils/table_pop.py — ne pas modifier à la main.',
              '',
              '/**',
              ' * Ce qui peut apparaître, par saison, par zone et par condition météo.',
              ' *',
              ' * Le relevé est celui de La Lune Eternelle, et c\'est la seule source connue',
              ' * pour cette correspondance : les sites publics disent quelles matières sont',
              ' * suprêmes à une saison, jamais dans quelle météo elles sortent.',
              ' *',
              ' * Il est **incomplet par construction** — il se remplit au fil des sorties des',
              ' * joueurs. Une case vide veut donc dire « pas encore relevé », et non « rien ».',
              ' */',
              'val POP: Map<String, Map<String, Map<String, Map<String, List<String>>>>> = mapOf(']
    for saison, zones in tout.items():
        lignes.append(f'    "{saison}" to mapOf(')
        for zone, conds in zones.items():
            lignes.append(f'        "{zone}" to mapOf(')
            for cond in CONDITIONS:
                if cond not in conds:
                    continue
                lignes.append(f'            "{cond.upper()}" to mapOf(')
                for famille, mats in conds[cond].items():
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


def main() -> int:
    dossier = sys.argv[1] if len(sys.argv) > 1 else None
    tout = collections.OrderedDict()
    for saison, gid in ONGLETS.items():
        table = lire(source(saison, gid, dossier))
        if not table:
            print(f"{saison} : rien de lu — classeur privé ou format changé ?",
                  file=sys.stderr)
            return 1
        tout[saison] = table
        total = sum(len(m) for z in table.values() for c in z.values()
                    for m in c.values())
        print(f"{saison:10} {len(table)} zones, {total:3} matières")
    cible = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "app/src/main/kotlin/net/ryzom/zyroom/model/PopTable.kt")
    with open(cible, "w", encoding="utf-8") as fh:
        fh.write(kotlin(tout))
    print("→", cible)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
