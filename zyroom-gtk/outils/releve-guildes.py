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
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from zyroom import alerts, movements, ryzom_api        # noqa: E402

#: Où le journal et l'état sont écrits, à la racine du dépôt.
DOSSIER = os.path.join(os.path.dirname(RACINE), "journaux")


def chemin(nom: str) -> str:
    return os.path.join(DOSSIER, nom)


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

    # Le premier relevé n'a rien à comparer : on pose l'état et on se tait.
    # Sans cette garde, tout le contenu des coffres entrerait au journal
    # comme s'il venait d'arriver.
    if not avant:
        alerts.save_snapshot(etat, apres)
        return entite.name, 0

    # `diff` compare aussi le trésor : il est rangé dans l'instantané sous
    # une clé réservée, et ressort de la même comparaison que les objets.
    bouges = movements.diff(avant, apres, entite)
    if bouges:
        movements.append(journal, bouges)
    alerts.save_snapshot(etat, apres)
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
    # Un échec de réseau ne doit pas peindre le dépôt en rouge tous les jours :
    # on ne signale l'erreur que si rien n'a pu être relevé.
    return 1 if ennuis and not total and ennuis == len(cles) else 0


if __name__ == "__main__":
    raise SystemExit(main())
