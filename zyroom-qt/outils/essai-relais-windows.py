#!/usr/bin/env python3
"""Le relais de mise à jour, essayé sur un vrai Windows.

**Pourquoi ce fichier existe.** Le relais n'a jamais démarré, sur aucune
machine, pendant une semaine : ses deux drapeaux de création s'excluent
mutuellement, `CreateProcess` refusait, et l'exception était avalée. Rien ne
l'a vu — ni les essais, qui ne lisaient que le texte du script, ni Wine, qui
accepte le mélange que Windows refuse, ni la relecture du code, qui cherchait
du côté des noms de dossiers.

Ce qu'il fallait, c'est une machine Windows. GitHub en prête une le temps d'un
essai : on y monte une installation de pacotille, on lance le relais pour de
vrai, et l'on regarde si les dossiers ont bougé.

    outils/essai-relais-windows.py            les deux essais
    outils/essai-relais-windows.py --app BAC  usage interne, voir plus bas

Rend zéro si tout tient, un sinon.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from zyroom import updater                                       # noqa: E402

NOM = "ZyRoom-Qt"
#: Le drapeau que Windows refuse en compagnie de DETACHED_PROCESS.
CREATE_NO_WINDOW = 0x08000000


def dire(bon: bool, texte: str) -> bool:
    print(f"  {'ok  ' if bon else 'RATE'}  {texte}")
    return bon


def essai_des_drapeaux() -> bool:
    """Windows refuse-t-il bien le mélange, et accepte-t-il le drapeau seul ?

    C'est le cœur du défaut. Si un jour Windows cessait de refuser, cet essai
    le dirait — et l'on saurait que la panne venait d'ailleurs.
    """
    print("Drapeaux de creation")
    ensemble = True

    try:
        p = subprocess.Popen(["cmd", "/c", "exit"],
                             creationflags=updater.DETACHED_PROCESS)
        p.wait(timeout=30)
        ensemble &= dire(True, "DETACHED_PROCESS seul : le processus demarre")
    except OSError as exc:
        ensemble &= dire(False, f"DETACHED_PROCESS seul a echoue : {exc}")

    # **Mesure, et non verdict.** On a cru un temps que le melange avec
    # CREATE_NO_WINDOW etait refuse par Windows et expliquait tout. Cet essai,
    # lance sur la machine de GitHub, a montre que non : il passe. La ligne
    # reste parce qu'elle documente le fait, mais elle ne decide de rien.
    try:
        p = subprocess.Popen(
            ["cmd", "/c", "exit"],
            creationflags=updater.DETACHED_PROCESS | CREATE_NO_WINDOW)
        p.wait(timeout=30)
        print("  note  le melange avec CREATE_NO_WINDOW est accepte ici")
    except OSError as exc:
        print(f"  note  le melange est refuse ici ({exc.errno})")

    return ensemble


def _poser(dossier: str, marque: str) -> None:
    os.makedirs(dossier, exist_ok=True)
    with open(os.path.join(dossier, "marqueur.txt"), "w") as f:
        f.write(marque)


def _lu(dossier: str) -> str:
    try:
        with open(os.path.join(dossier, "marqueur.txt")) as f:
            return f.read().strip()
    except OSError:
        return ""


def joue_l_application(bac: str) -> int:
    """Se fait passer pour l'application, lance le relais, et meurt.

    Le relais attend notre disparition avant de permuter : il faut donc un
    processus qui parte pour de bon, et non un appel dans celui qui mesure.
    """
    sys.frozen = True
    sys.executable = os.path.join(bac, NOM + updater.SUFFIXE_NOUVEAU,
                                  NOM + ".exe")
    parti = updater._relais_windows(
        relancer_apres=False, journal=os.path.join(bac, "journal.txt"))
    print(f"    (relais parti : {parti}; raison : "
          f"{updater.derniere_erreur or 'aucune'})")
    return 0 if parti else 1


def essai_de_permutation() -> bool:
    """Le décor du joueur : une version qui attend à côté, jamais mise en place."""
    print("Permutation des dossiers")
    bac = tempfile.mkdtemp(prefix="essai-relais-")
    maison = os.path.join(bac, NOM)
    attente = maison + updater.SUFFIXE_NOUVEAU
    _poser(maison, "ancienne")
    _poser(attente, "neuve")

    fils = subprocess.run(
        [sys.executable, os.path.abspath(__file__), "--app", bac],
        capture_output=True, text=True, timeout=120)
    print(fils.stdout.rstrip() or "    (le fils n'a rien dit)")
    if fils.returncode != 0:
        return dire(False, f"le relais n'est pas parti : {fils.stderr[-400:]}")

    # Le relais attend la mort du fils, puis permute. Deux minutes de
    # patience : sa boucle d'attente peut a elle seule durer une minute, et
    # trente secondes ne suffisaient pas -- on concluait avant lui.
    for _ in range(240):
        if _lu(maison) == "neuve" and not os.path.isdir(attente):
            break
        time.sleep(0.5)

    journal = os.path.join(bac, "journal.txt")
    print("    journal du relais :")
    if os.path.isfile(journal):
        with open(journal) as f:
            for ligne in f:
                print("      " + ligne.rstrip())
    else:
        print("      (aucun : le script n'a pas demarre du tout)")
    print(f"    ce qui reste dans le bac : {sorted(os.listdir(bac))}")

    ensemble = dire(_lu(maison) == "neuve",
                    "la nouvelle version a pris la place de l'ancienne")
    ensemble &= dire(not os.path.isdir(attente),
                     "le dossier .nouveau a disparu")
    return ensemble


def main() -> int:
    if os.name != "nt":
        print("Cet essai ne veut rien dire hors de Windows.")
        return 0
    if len(sys.argv) > 2 and sys.argv[1] == "--app":
        return joue_l_application(sys.argv[2])

    tout = essai_des_drapeaux()
    tout &= essai_de_permutation()
    print("\n" + ("Le relais fonctionne." if tout
                  else "Le relais ne fonctionne PAS."))
    return 0 if tout else 1


if __name__ == "__main__":
    sys.exit(main())
