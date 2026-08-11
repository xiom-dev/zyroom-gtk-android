#!/usr/bin/env python3
"""Fabrique les tables de noms d'avant-postes des deux portages.

Source : `nimetu/ryzom_extra`, branche `json-resources`, qui publie les
feuilles du jeu en JSON sous LGPL-3.0. C'est le dépôt que la documentation de
l'API de Ryzom recommande elle-même pour les traductions.

    https://github.com/nimetu/ryzom_extra

Pourquoi les figer plutôt que de lire le pack du client : `string_client.pack`
fait deux mégaoctets et demi, sa licence n'est pas établie, et il n'est donc
embarqué que dans les variantes qu'on distribue soi-même. La variante F-Droid
n'en a pas, et affichait des codes bruts — « fyros_outpost_04 » au lieu de
« Ferme de Malmontagne ».

Ces noms-ci pèsent deux kilo-octets, portent une licence claire, et servent de
recours dans **toutes** les variantes : le pack, quand il est là, reste
prioritaire — c'est la source du jeu lui-même.

    python3 outils/table_avant_postes.py
"""
import json
import os
import urllib.request

SOURCE = ("https://raw.githubusercontent.com/nimetu/ryzom_extra/"
          "json-resources/resources/sheets-cache/words_fr_outpost.json")

#: Ce qu'on ne garde pas : les quatre avant-postes des Primes portent
#: « ((En test, instable)) » dans leur nom et « Outpost used for
#: experimentations » en guise de description. Ils n'ont jamais été ouverts au
#: jeu ; afficher leur nom de travail vaudrait moins que de ne rien afficher.
MARQUE_INSTABLE = "En test"


def charge() -> dict:
    with urllib.request.urlopen(SOURCE, timeout=60) as reponse:
        return json.loads(reponse.read().decode("utf-8"))


def noms(brut: dict) -> "dict[str, str]":
    retenus = {}
    for code, fiche in sorted(brut.items()):
        nom = (fiche.get("name") or "").strip()
        if not nom or MARQUE_INSTABLE in nom:
            continue
        retenus[code] = nom
    return retenus


def kotlin(table: dict) -> str:
    lignes = ['package net.ryzom.zyroom.model', '',
              '// Fichier produit par outils/table_avant_postes.py — ne pas',
              '// modifier à la main.',
              '',
              '/**',
              " * Le nom français de chaque avant-poste, à défaut du pack du jeu.",
              ' *',
              " * Relevé de `nimetu/ryzom_extra` (LGPL-3.0), que la documentation de",
              " * l'API de Ryzom recommande pour les traductions. Le pack du client",
              " * reste prioritaire quand il est là : c'est la source du jeu lui-même,",
              " * et elle suit ses mises à jour. Ceci sert la variante F-Droid, qui ne",
              " * peut pas embarquer le pack, et tout exemplaire dont l'import a échoué.",
              ' */',
              'val NOMS_AVANT_POSTES: Map<String, String> = mapOf(']
    for code, nom in table.items():
        lignes.append(f'    "{code}" to "{nom}",')
    lignes.append(')')
    return "\n".join(lignes) + "\n"


def python(table: dict) -> str:
    lignes = ['"""Le nom français de chaque avant-poste, à défaut du pack du jeu.',
              '',
              'Fichier produit par ../zyroom-android/outils/table_avant_postes.py —',
              'ne pas modifier à la main.',
              '',
              "Relevé de `nimetu/ryzom_extra` (LGPL-3.0), que la documentation de l'API",
              'de Ryzom recommande pour les traductions. Le pack du client reste',
              "prioritaire quand il est là : c'est la source du jeu lui-même, et elle",
              'suit ses mises à jour.',
              '"""',
              '',
              '#: {code de l\'avant-poste: nom français}',
              'NOMS_AVANT_POSTES = {']
    for code, nom in table.items():
        lignes.append(f'    "{code}": "{nom}",')
    lignes.append('}')
    return "\n".join(lignes) + "\n"


def main() -> int:
    brut = charge()
    table = noms(brut)
    print(f"{len(brut)} avant-postes décrits, {len(table)} retenus "
          f"({len(brut) - len(table)} écartés comme instables)")

    android = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    depot = os.path.dirname(android)
    for cible, contenu in (
        (os.path.join(android,
                      "app/src/main/kotlin/net/ryzom/zyroom/model/OutpostNames.kt"),
         kotlin(table)),
        (os.path.join(depot, "zyroom-gtk/zyroom/noms_avant_postes.py"),
         python(table)),
    ):
        if not os.path.isdir(os.path.dirname(cible)):
            print("passé :", cible, "(dossier absent)")
            continue
        with open(cible, "w", encoding="utf-8") as fh:
            fh.write(contenu)
        print("→", cible)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
