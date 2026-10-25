#!/usr/bin/env python3
"""Le relevé qui tourne sur GitHub, sans qu'aucune machine soit allumée.

L'API de Ryzom ne rend qu'un état, jamais un historique : un mouvement se
déduit de deux relevés successifs, et chaque installation ne connaît donc que
ce qu'elle a regardé elle-même. Un officier qui relève une fois par semaine
voit d'un bloc ce qu'un autre a vu en trois fois — et personne ne voit ce qui
s'est passé pendant que tout le monde dormait.

Ce script est le relevé que personne n'a à faire. Il tourne sur les serveurs
de GitHub, à l'heure, interroge la guilde, tient son journal et le versionne.
Les applications le relisent au lancement et le fusionnent au leur ; elles ne
font que lire une adresse publique, sans jeton ni compte.

**Il réutilise le code du bureau**, et ne le recopie pas : `ryzom_api`,
`alerts` et `movements` s'importent sans GTK, et deux implémentations du même
calcul auraient dérivé l'une de l'autre au premier correctif.

Les clés viennent de l'environnement, jamais du dépôt :

    CLES_GUILDES="g4736…,gdc2e…"   # secret du dépôt, séparées par virgules

L'état de chaque guilde vit à côté de son journal, versionné avec lui : sans
lui, le premier relevé suivant croirait que tout vient d'arriver.
"""
from __future__ import annotations

import json
import os
import re
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from zyroom import alerts, movements, roster, ryzom_api  # noqa: E402

#: Où le journal et l'état sont écrits.
#:
#: Le relevé programmé y pointe la copie de travail de la branche `journaux`,
#: qu'il pousse ensuite en force : cette branche est orpheline et n'a donc
#: aucun historique à faire grossir. Hors GitHub, le dossier voisin du dépôt
#: fait l'affaire pour essayer.
DOSSIER = os.environ.get("DOSSIER_JOURNAUX") or os.path.join(
    os.path.dirname(RACINE), "journaux")


def chemin(nom: str) -> str:
    return os.path.join(DOSSIER, nom)


#: Les armures et les bijoux craftes : "ic", le peuple, puis "a" (armure) ou
#: "j" (bijou). C'est ce que la page xiom.be/mp range en tenues completes.
ARMURE_OU_BIJOU = re.compile(r"^ic[a-z][aj]")

#: Le bonus d'un objet, une lettre par jauge : vie, seve, endurance,
#: concentration. Les bijoux se trient par bonus (demande de Nizyros).
BONUS = (("v", "hp_buff"), ("s", "sap_buff"), ("e", "sta_buff"),
         ("c", "focus_buff"))


def tenues(entite) -> dict[str, int]:
    """Les armures et bijoux du hall, "fiche|qualite|bonus" -> nombre.

    Un fichier a part, et non une cle de plus dans l'etat : l'etat sert a
    deduire les mouvements, et le bonus n'y a pas sa place -- deux bagues
    identiques sauf le bonus y restent une seule pile.
    """
    compte: dict[str, int] = {}
    for inventaire in entite.inventories:
        for objet in inventaire.items:
            if not ARMURE_OU_BIJOU.match(objet.sheet):
                continue
            bonus = "".join(l for l, attr in BONUS if getattr(objet, attr, 0))
            cle = f"{objet.sheet}|{objet.quality}|{bonus}"
            compte[cle] = compte.get(cle, 0) + max(1, objet.stack)
    return dict(sorted(compte.items()))


def usure(entite) -> dict[str, list[int]]:
    """La piece la plus usee de chaque pile, "fiche|qualite|bonus" -> [hp, max].

    Un fichier a part de `tenues` : la page xiom.be/mp affiche la durabilite
    d'une armure ou d'une parure a cote de sa qualite. On garde la piece la
    plus entamee (le rapport hp / max le plus bas), c'est elle qui lachera
    la premiere.
    """
    pire: dict[str, list[int]] = {}
    for inventaire in entite.inventories:
        for objet in inventaire.items:
            if not ARMURE_OU_BIJOU.match(objet.sheet) or not objet.hp_max:
                continue
            bonus = "".join(l for l, attr in BONUS if getattr(objet, attr, 0))
            cle = f"{objet.sheet}|{objet.quality}|{bonus}"
            avant = pire.get(cle)
            if avant is None or objet.hp * avant[1] < avant[0] * objet.hp_max:
                pire[cle] = [objet.hp, objet.hp_max]
    return dict(sorted(pire.items()))


def entamees(entite) -> dict[str, list[list[int]]]:
    """Chaque objet entame hors armures et bijoux, "fiche|qualite" -> [[hp, max, n]].

    Pour l'onglet Armes de xiom.be/mp : un site de gestion des stocks, donc
    toutes les pieces entamees, une par une, et non la seule plus usee. Une
    pile identique (meme durabilite) ne fait qu'une entree, avec son nombre.
    """
    compte: dict[str, dict[tuple[int, int], int]] = {}
    for inventaire in entite.inventories:
        for objet in inventaire.items:
            if (ARMURE_OU_BIJOU.match(objet.sheet) or not objet.hp_max
                    or objet.hp >= objet.hp_max):
                continue
            pile = compte.setdefault(f"{objet.sheet}|{objet.quality}", {})
            hp = (objet.hp, objet.hp_max)
            pile[hp] = pile.get(hp, 0) + max(1, objet.stack)
    return {cle: [[hp, mx, n] for (hp, mx), n in sorted(pile.items())]
            for cle, pile in sorted(compte.items())}


def relever(cle: str) -> tuple[str, int]:
    """Relève une guilde et verse ce qui a bougé dans son journal.

    Renvoie (nom de la guilde, mouvements ajoutés). Une clé qui ne répond pas
    n'arrête pas les autres : mieux vaut un journal partiel qu'aucun.
    """
    entite = ryzom_api.parse_guild(ryzom_api.fetch_guild_xml(cle), lambda s: s)
    journal = chemin(f"guild-{entite.entity_id}.jsonl")
    etat = chemin(f"guild-{entite.entity_id}-etat.json")

    avant = alerts.load_snapshot(etat)
    apres = alerts.build_snapshot(entite)

    with open(chemin(f"guild-{entite.entity_id}-tenues.json"), "w",
              encoding="utf-8") as fh:
        json.dump(tenues(entite), fh, separators=(",", ":"))
        fh.write("\n")
    with open(chemin(f"guild-{entite.entity_id}-usure.json"), "w",
              encoding="utf-8") as fh:
        json.dump(usure(entite), fh, separators=(",", ":"))
        fh.write("\n")
    with open(chemin(f"guild-{entite.entity_id}-entamees.json"), "w",
              encoding="utf-8") as fh:
        json.dump(entamees(entite), fh, separators=(",", ":"))
        fh.write("\n")

    # Le premier releve n'a rien a comparer : on pose l'etat et on se tait.
    # Sans cette garde, tout le contenu des coffres entrerait au journal
    # comme s'il venait d'arriver.
    if not avant:
        alerts.save_snapshot(etat, apres)
        return entite.name, 0

    # `diff` compare aussi le tresor : il est range dans l'instantane sous
    # une cle reservee, et ressort de la meme comparaison que les objets.
    bouges = movements.diff(avant, apres, entite)
    if bouges:
        movements.append(journal, bouges)
    alerts.save_snapshot(etat, apres)

    # Le registre du personnel, tenu ici aussi. Il ne se deduit pas des
    # coffres mais de l'effectif, et personne d'autre ne le tient a l'heure :
    # une application ouverte deux fois par semaine ne voit qu'un membre sur
    # trois passer. Six mois d'arrivees et de departs finissent par valoir
    # plus que le journal des coffres.
    if entite.members:
        roster.RosterStore(DOSSIER, entite.entity_id).record(entite.members)
    return entite.name, len(bouges)


def main() -> int:
    brut = os.environ.get("CLES_GUILDES", "").strip()
    if not brut:
        print("CLES_GUILDES est vide : rien à relever.", file=sys.stderr)
        return 1

    cles = [c.strip() for c in brut.replace(";", ",").split(",") if c.strip()]
    os.makedirs(DOSSIER, exist_ok=True)
    total = 0
    ennuis = 0
    for cle in cles:
        if not ryzom_api.is_api_key(cle):
            print(f"  clé ignorée : {cle[:8]}… n'a pas la forme d'une clé")
            ennuis += 1
            continue
        try:
            nom, combien = relever(cle)
        except Exception as souci:          # noqa: BLE001 — on continue
            print(f"  échec sur {cle[:8]}… : {souci}")
            ennuis += 1
            continue
        total += combien
        print(f"  {nom} : {combien} mouvement(s)")

    print(f"{total} mouvement(s) au total")
    # Un echec de reseau ne doit pas peindre le depot en rouge tous les
    # jours : on ne signale l'erreur que si rien n'a pu etre releve.
    return 1 if ennuis and not total and ennuis == len(cles) else 0


if __name__ == "__main__":
    raise SystemExit(main())
