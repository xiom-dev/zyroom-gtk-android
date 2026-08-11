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

#: D'où viennent les symboles des familles de matières.
#:
#: Relevé dans le code du site — `/images/tracker_icon/` + le nom de l'icône
#: avec sa première lettre en capitale. Ce sont les symboles du jeu : une
#: coquille pour la carapace, une goutte pour la sève. Ils sont **téléchargés
#: une fois et embarqués**, comme le reste du relevé : l'application doit tenir
#: le jour où ce site fermera.
ICONES = "https://www.ryzomarmory.com/images/tracker_icon"
SAISONS = {"PRINTEMPS": "spring", "ETE": "summer",
           "AUTOMNE": "autumn", "HIVER": "winter"}

#: {groupe français: nom de l'icône}, rempli en lisant l'API.
#:
#: Recopier cette correspondance à la main la ferait diverger du jour où Ryzom
#: ajouterait une famille : elle se déduit du flux, comme le reste.
SYMBOLES: "collections.OrderedDict[str, str]" = collections.OrderedDict()

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
        icone = groupe["materialGroup"].get("icon")
        if icone:
            SYMBOLES[nom_fr] = icone
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
    l += [')', '',
          '/**',
          ' * Le symbole de chaque famille de matières.',
          ' *',
          " * Le nom d'une ressource Android, sans extension : « Carapace » se",
          ' * dessine `R.drawable.mp_shell`. Les images sont embarquées, comme les',
          ' * listes — rien ne se télécharge à la lecture du tableau.',
          ' */',
          'val SYMBOLES: Map<String, String> = mapOf(']
    for groupe, icone in SYMBOLES.items():
        l.append(f'    "{groupe}" to "{icone}",')
    l.append(')')
    return "\n".join(l) + "\n"


def python(supremes: dict, excellentes: dict) -> str:
    """Le même relevé, pour le portage GTK.

    Deux fichiers produits d'un seul geste : une table recopiée à la main d'un
    langage à l'autre finit toujours par diverger, et personne ne s'en aperçoit
    avant de comparer les deux applications côte à côte."""
    l = ['"""Les matières suprêmes et excellentes, par saison.',
         '',
         'Fichier produit par ../zyroom-android/outils/table_armory.py — ne pas',
         'modifier à la main. Relevé de Ryzom Armory, figé ici : ces listes ne',
         "changent qu'avec le jeu, et l'application doit tenir le jour où ce site",
         'fermera.',
         '"""',
         '',
         '#: {saison: {zone des Primes: {groupe: [noms]}}}',
         'SUPREMES = {']
    for saison, zones in supremes.items():
        l.append(f'    "{saison}": {{')
        for zone, groupes in zones.items():
            l.append(f'        "{zone}": {{')
            for groupe, noms in groupes.items():
                l.append(f'            "{groupe}": [' +
                         ", ".join(f'"{n}"' for n in noms) + '],')
            l.append('        },')
        l.append('    },')
    l += ['}', '',
          '#: {saison: {"JOUR"|"NUIT": {groupe: [noms]}}}',
          "#: L'API ne les répartit pas par zone mais par moment de la journée :",
          "#: c'est ainsi que le jeu les fait apparaître.",
          'EXCELLENTES = {']
    for saison, moments in excellentes.items():
        l.append(f'    "{saison}": {{')
        for moment, groupes in moments.items():
            l.append(f'        "{moment}": {{')
            for groupe, noms in groupes.items():
                l.append(f'            "{groupe}": [' +
                         ", ".join(f'"{n}"' for n in noms) + '],')
            l.append('        },')
        l.append('    },')
    l += ['}', '',
          '#: {groupe: nom du symbole}, sans extension ni chemin.',
          'SYMBOLES = {']
    for groupe, icone in SYMBOLES.items():
        l.append(f'    "{groupe}": "{icone}",')
    l.append('}')
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

    android = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    depot = os.path.dirname(android)

    # Les symboles, une fois pour toutes. `drawable-nodpi` : ces images font
    # quarante pixels de côté et l'écran leur donne une taille en points — les
    # ranger dans un seuil de densité les ferait redimensionner deux fois.
    dessins = os.path.join(android, "app/src/main/res/drawable-nodpi")
    os.makedirs(dessins, exist_ok=True)
    for icone in SYMBOLES.values():
        cible = os.path.join(dessins, icone + ".png")
        if os.path.isfile(cible):
            continue
        nom = icone[0].upper() + icone[1:]
        with urllib.request.urlopen(f"{ICONES}/{nom}.png", timeout=60) as reponse:
            with open(cible, "wb") as fh:
                fh.write(reponse.read())
        print("symbole →", cible)
    for chemin, contenu in (
        (os.path.join(android,
                      "app/src/main/kotlin/net/ryzom/zyroom/model/ArmoryTable.kt"),
         kotlin(supremes, excellentes)),
        (os.path.join(depot, "zyroom-gtk/zyroom/armory.py"),
         python(supremes, excellentes)),
    ):
        if not os.path.isdir(os.path.dirname(chemin)):
            print("passé :", chemin, "(dossier absent)")
            continue
        with open(chemin, "w", encoding="utf-8") as fh:
            fh.write(contenu)
        print("→", chemin)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
