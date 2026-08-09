#!/usr/bin/env python3
"""Fabrique `model/ArmoryTable.kt` — les matières suprêmes et excellentes.

Source : l'API de Ryzom Armory, qui recense pour chaque saison les matières
suprêmes par zone des Primes et les excellentes de jour et de nuit.

    https://api.ryzomarmory.com/gamedata/tracker/{supremes,excellents}/{saison}

Les données sont **figées dans l'application** plutôt qu'interrogées à chaque
ouverture : elles ne changent qu'avec le jeu, et l'application doit continuer
de fonctionner le jour où ce site fermera. À relancer si Ryzom modifie ses
matières.

    python3 outils/table_armory.py
"""
import collections
import json
import os
import urllib.request

BASE = "https://api.ryzomarmory.com/gamedata/tracker"
SAISONS = {"PRINTEMPS": "spring", "ETE": "summer",
           "AUTOMNE": "autumn", "HIVER": "winter"}

#: Groupes de matières, de l'anglais de l'API vers le français du jeu.
GROUPES = {
    "Amber": "Ambres", "Seed": "Graines", "Fiber": "Fibres", "Resin": "Résine",
    "Oil": "Huile", "Sap": "Sève", "Shell": "Carapace", "Bark": "Écorce",
    "Wood": "Bois", "Node": "Boucles", "Wood Node": "Boucles",
}

#: Zones, de l'anglais de l'API vers le français employé dans la guilde.
ZONES = {
    "Under Spring": "Sources Interdites",
    "Land of Continuity": "Terre de la Continuité",
    "Sunken City": "Cité Engloutie",
    "Forbidden Depths": "Profondeurs Interdites",
}


def charge(chemin: str):
    with urllib.request.urlopen(f"{BASE}/{chemin}", timeout=60) as reponse:
        return json.loads(reponse.read().decode("utf-8"))


def matieres(groupes: list) -> "collections.OrderedDict[str, list[str]]":
    """{groupe français: [noms courts]} — « Silvio Seed » devient « Silvio ».

    Le suffixe répète le groupe, déjà porté par la colonne : le garder
    doublerait chaque ligne sans rien apprendre."""
    out = collections.OrderedDict()
    for groupe in groupes:
        nom_en = groupe["materialGroup"]["name"]
        nom_fr = GROUPES.get(nom_en, nom_en)
        noms = []
        for famille in groupe["materialFamilies"]:
            court = famille["name"]
            if court.endswith(" " + nom_en):
                court = court[: -len(nom_en) - 1]
            noms.append(court)
        if noms:
            out[nom_fr] = sorted(noms)
    return out


def kotlin(supremes: dict, excellentes: dict) -> str:
    l = ['package net.ryzom.zyroom.model', '',
         '// Fichier produit par outils/table_armory.py — ne pas modifier à la main.',
         '',
         '/**',
         " * Les matières suprêmes, par saison et par zone des Primes.",
         ' *',
         " * Relevé de Ryzom Armory, figé ici : ces listes ne changent qu'avec le jeu,",
         " * et l'application doit tenir le jour où ce site fermera.",
         ' */',
         'val SUPREMES: Map<String, Map<String, Map<String, List<String>>>> = mapOf(']
    for saison, zones in supremes.items():
        l.append(f'    "{saison}" to mapOf(')
        for zone, groupes in zones.items():
            l.append(f'        "{zone}" to mapOf(')
            for groupe, noms in groupes.items():
                l.append(f'            "{groupe}" to listOf(' +
                         ", ".join(f'"{n}"' for n in noms) + '),')
            l.append('        ),')
        l.append('    ),')
    l += [')', '',
          '/**',
          " * Les matières excellentes, par saison, de jour et de nuit.",
          ' *',
          " * L'API ne les répartit pas par zone mais par moment de la journée :",
          " * c'est ainsi que le jeu les fait apparaître.",
          ' */',
          'val EXCELLENTES: Map<String, Map<String, Map<String, List<String>>>> = mapOf(']
    for saison, moments in excellentes.items():
        l.append(f'    "{saison}" to mapOf(')
        for moment, groupes in moments.items():
            l.append(f'        "{moment}" to mapOf(')
            for groupe, noms in groupes.items():
                l.append(f'            "{groupe}" to listOf(' +
                         ", ".join(f'"{n}"' for n in noms) + '),')
            l.append('        ),')
        l.append('    ),')
    l.append(')')
    return "\n".join(l) + "\n"


def main() -> int:
    supremes, excellentes = collections.OrderedDict(), collections.OrderedDict()
    for saison, anglais in SAISONS.items():
        par_zone = collections.OrderedDict()
        for bloc in charge(f"supremes/{anglais}"):
            nom = bloc["region"]["translation"]["name"]
            par_zone[ZONES.get(nom, nom)] = matieres(bloc["materials"])
        supremes[saison] = par_zone

        moments = collections.OrderedDict()
        for cle, groupes in charge(f"excellents/{anglais}").items():
            moments["JOUR" if cle == "day" else "NUIT"] = matieres(groupes)
        excellentes[saison] = moments

        n_sup = sum(len(v) for z in par_zone.values() for v in z.values())
        n_exc = sum(len(v) for m in moments.values() for v in m.values())
        print(f"{saison:10} {n_sup:3} suprêmes ({len(par_zone)} zones), "
              f"{n_exc:3} excellentes ({', '.join(moments)})")

    cible = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "app/src/main/kotlin/net/ryzom/zyroom/model/ArmoryTable.kt")
    with open(cible, "w", encoding="utf-8") as fh:
        fh.write(kotlin(supremes, excellentes))
    print("→", cible)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
