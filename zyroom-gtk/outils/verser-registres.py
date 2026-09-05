#!/usr/bin/env python3
"""Verse dans le registre publié ce que les applications d'ici ont vu.

Le relevé horaire tourne sur GitHub et voit tout, à l'heure près — mais il ne
tourne que depuis sa mise en place. Ce que les applications ont constaté
avant lui, ou pendant une panne de clé, n'existe que sur cette machine : six
mouvements publiés quand ZyRoom-Qt en avait soixante et ZyRoom-GTK cinquante
et un, aucune des trois n'étant complète.

Ce script est le chemin **montant**, celui que les applications n'ont pas :
elles lisent une adresse publique sans jeton ni compte, et c'est ce qui les
rend sûres à distribuer. Le versement, lui, demande le droit d'écrire sur le
dépôt — il se fait donc d'ici, à la main, quand on juge qu'il y a matière.

    ./verser-registres.py              montre ce qui serait versé
    ./verser-registres.py --pousser    verse et publie

Le rapprochement passe par `roster.fusionner`, comme dans les applications :
deux constats du même mouvement portent la date du relevé qui les a vus, pas
celle du fait, et une comparaison stricte en ferait deux mouvements. La date
la plus ancienne l'emporte — l'événement précède toujours son constat.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from zyroom import roster  # noqa: E402

#: Le dépôt qui porte la branche `journaux`.
DEPOT = "git@github.com:xiom-dev/zyroom-gtk-android.git"

#: Les guildes suivies. Les mêmes que le secret `CLES_GUILDES` du relevé
#: horaire, sans les clés : ici on ne parle à l'API de personne, on ne fait
#: que rapprocher des journaux déjà écrits.
GUILDES = ("105906237", "105908280")

#: Où les applications tiennent leur registre, sur cette machine.
#:
#: Les deux Flatpak d'abord — ce sont les installations qui servent — puis
#: les emplacements hors bac à sable, qu'une exécution depuis les sources
#: alimente. Un chemin absent est simplement sauté.
REGISTRES = (
    ("ZyRoom-Qt", "~/.local/share/zyroom-qt"),
    ("ZyRoom-GTK (dev)", "~/.var/app/net.ryzom.zyroomgtk.dev/data/zyroom-gtk"),
    ("ZyRoom-GTK (guilde)", "~/.var/app/net.ryzom.zyroomgtk/data/zyroom-gtk"),
    ("ZyRoom-GTK (sources)", "~/.local/share/zyroom-gtk"),
)


def lire(chemin: str) -> tuple[list[roster.Change], list[str]]:
    """Le registre d'un fichier, et les lignes qu'on n'a pas su lire.

    Les illisibles sont rendues telles quelles : un journal n'est pas
    remplaçable, et une ligne tronquée par une coupure vaut mieux que rien.
    """
    mouvements: list[roster.Change] = []
    illisibles: list[str] = []
    try:
        with open(chemin, encoding="utf-8") as fh:
            for ligne in fh:
                ligne = ligne.strip()
                if not ligne:
                    continue
                try:
                    d = json.loads(ligne)
                    mouvements.append(roster.Change(
                        int(d["at"]), d.get("member", ""), d.get("kind", ""),
                        d.get("from", ""), d.get("to", "")))
                except (ValueError, KeyError, TypeError):
                    illisibles.append(ligne)
    except OSError:
        pass
    return mouvements, illisibles


def ecrire(chemin: str, mouvements: list[roster.Change],
           illisibles: list[str]) -> None:
    with open(chemin, "w", encoding="utf-8") as fh:
        for brut in illisibles:
            fh.write(brut + "\n")
        for c in mouvements:
            fh.write(json.dumps({"at": c.at, "member": c.member,
                                 "kind": c.kind, "from": c.frm,
                                 "to": c.to}, ensure_ascii=False) + "\n")


def main() -> int:
    pousser = "--pousser" in sys.argv[1:]

    with tempfile.TemporaryDirectory(prefix="registres-") as travail:
        clone = os.path.join(travail, "journaux")
        fait = subprocess.run(
            ["git", "clone", "--quiet", "--branch", "journaux", "--depth", "1",
             DEPOT, clone],
            capture_output=True, text=True)
        if fait.returncode != 0:
            print(f"Impossible de lire la branche « journaux » : {fait.stderr.strip()}",
                  file=sys.stderr)
            return 1

        bouge = False
        for guilde in GUILDES:
            publie_chemin = os.path.join(clone, f"roster-{guilde}.jsonl")
            publies, illisibles = lire(publie_chemin)
            print(f"\nGuilde {guilde} — {len(publies)} mouvement(s) publié(s)")

            fusionnes = publies
            for nom, dossier in REGISTRES:
                local = os.path.expanduser(os.path.join(dossier, f"roster-{guilde}.jsonl"))
                if not os.path.isfile(local):
                    continue
                locaux, _ = lire(local)
                fusionnes, ajoutes = roster.fusionner(fusionnes, locaux)
                marque = f"+{ajoutes}" if ajoutes else "  ="
                print(f"    {marque:>4}  {nom} ({len(locaux)} ligne(s))")

            # La fusion dédoublonne aussi ce qui était déjà publié : le premier
            # versement, fait à la main, avait laissé treize constats répétés
            # d'un même fait — Ysatia « partie » trois fois sans être revenue.
            fusionnes, _ = roster.fusionner(fusionnes, [])
            if len(fusionnes) == len(publies):
                print("    rien à verser")
                continue
            print(f"    → {len(fusionnes)} mouvement(s) après fusion")
            ecrire(publie_chemin, fusionnes, illisibles)
            bouge = True

        if not bouge:
            print("\nRien à verser : le registre publié sait déjà tout.")
            return 0
        if not pousser:
            print("\nRien n'a été envoyé. Relancez avec --pousser pour publier.")
            return 0

        message = ("Le registre reprend ce que les applications avaient vu\n\n"
                   "Versé par outils/verser-registres.py.\n")
        for commande in (["git", "add", "-A"],
                         ["git", "-c", "user.name=Ludo",
                          "-c", "user.email=ludopika@gmail.com",
                          "commit", "--quiet", "-m", message],
                         ["git", "push", "--quiet", "origin", "journaux"]):
            fait = subprocess.run(commande, cwd=clone, capture_output=True, text=True)
            if fait.returncode != 0:
                print(f"Échec de « {' '.join(commande[:2])} » : {fait.stderr.strip()}",
                      file=sys.stderr)
                return 1
        print("\nRegistre publié.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
