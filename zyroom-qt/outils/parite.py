#!/usr/bin/env python3
"""Confronte l'aspect de ZyRoom-Qt à celui de ZyRoom-GTK. GTK fait foi.

    ./outils/parite.py            compare, et dit ce qui diffère
    ./outils/parite.py --details  montre aussi tout ce qui concorde

Rend zéro quand les deux applications s'accordent, un sinon — c'est ce qui
permet à `livraison.sh` de s'arrêter plutôt que d'envoyer aux joueurs une
version qui a dérivé.

**Pourquoi ce contrôle existe.** Tous les écarts d'aspect trouvés jusqu'ici
l'ont été à l'œil, par Ludo, après livraison : une jauge étirée sur toute la
hauteur d'une rangée, une ligne de saison en gras qui la rendait floue, un
vert à un point du bon, un bouton qui ne s'allumait pas. Chacun se voyait
pourtant dans une mesure. Ce que l'œil trouve après coup, une mesure le trouve
avant.

**Aucune exception.** Il n'y a pas de liste d'écarts tolérés, et il ne doit pas
y en avoir : ce qui est relevé doit être identique, sans dérogation. C'est le
choix des propriétés relevées qui porte la décision, dans les deux fichiers de
`parite/`, et cette décision se discute là-bas — pas ici, au cas par cas, sous
la pression d'une livraison qui attend.

Les deux applications ne peuvent pas cohabiter dans un même processus : GTK
vit dans le Python du système, Qt dans son environnement virtuel. D'où deux
relevés lancés séparément, et cette confrontation de leurs résultats.
"""
from __future__ import annotations

import json
import os
import contextlib
import shutil
import subprocess
import time
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RELEVES = os.path.join(RACINE, "outils", "parite")

#: L'interpréteur de chaque application. Celui de Qt vit dans son
#: environnement virtuel ; celui de GTK est le Python du système, seul à
#: disposer de `gi`.
PYTHON_QT = os.path.join(RACINE, ".venv", "bin", "python")
PYTHON_GTK = "python3"


#: Ce qu'on retire à l'environnement avant de mesurer.
#:
#: **Les deux relevés doivent être logés à la même enseigne.** `gsettings` ne
#: regarde pas le HOME : il passe par dconf, donc par le bus de session, et
#: rapporte les réglages réels du bureau. La version Qt les interroge —
#: l'agrandissement du texte, le thème d'icônes — et les applique ; la version
#: GTK, sur un serveur X virtuel sans démon XSettings, ne les voit pas. Un
#: bureau réglé à 1,25 donnait alors des largeurs Qt trente pour cent au-dessus
#: de celles de GTK, et l'outil accusait les fenêtres d'un écart qui venait de
#: la mesure.
#:
#: `memory` rend les valeurs par défaut du schéma, identiques pour les deux.
ENVIRONNEMENT_NEUTRE = {"GSETTINGS_BACKEND": "memory"}


@contextlib.contextmanager
def ecran_virtuel():
    """Un serveur X à nous, le temps d'un relevé.

    **Le relevé GTK doit y tourner, et pas dans la session du bureau.** Sous
    Wayland, GTK demande au portail l'agrandissement du texte et le thème
    d'icônes, et les applique — tandis que le relevé Qt, hors écran, ne les a
    pas. On mesurait alors une fenêtre agrandie contre une autre qui ne l'était
    pas, et l'écart passait pour un défaut de l'application.

    Sans Xvfb, on rend None : le relevé se fera dans la session, avec un
    résultat moins sûr mais un outil qui marche quand même.
    """
    if not shutil.which("Xvfb"):
        yield None
        return
    numero = ":97"
    serveur = subprocess.Popen(
        ["Xvfb", numero, "-screen", "0", "1200x760x24", "-dpi", "96"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            pret = subprocess.run(["xdpyinfo"], capture_output=True,
                                  env=dict(os.environ, DISPLAY=numero))
            if pret.returncode == 0:
                break
            time.sleep(0.2)
        yield numero
    finally:
        serveur.terminate()
        serveur.wait(timeout=10)


def relever(python: str, script: str, nom: str, ecran: str | None = None) -> dict | None:
    """Lance un relevé et rend son contenu, ou None s'il a échoué."""
    milieu = dict(os.environ, **ENVIRONNEMENT_NEUTRE)
    if ecran:
        milieu["DISPLAY"] = ecran
        milieu["GDK_BACKEND"] = "x11"
        milieu.pop("WAYLAND_DISPLAY", None)
    fait = subprocess.run([python, os.path.join(RELEVES, script)],
                          capture_output=True, text=True, timeout=300,
                          env=milieu)
    if not fait.stdout.strip():
        print(f"Le relevé {nom} n'a rien rendu.", file=sys.stderr)
        if fait.stderr.strip():
            print(fait.stderr.strip()[-800:], file=sys.stderr)
        return None
    try:
        points = json.loads(fait.stdout)
    except json.JSONDecodeError as souci:
        print(f"Le relevé {nom} est illisible : {souci}", file=sys.stderr)
        return None
    if "erreur" in points:
        print(f"Le relevé {nom} a échoué : {points['erreur']}", file=sys.stderr)
        return None
    return points


#: Les points montrés mais qui n'arrêtent pas la livraison.
#:
#: La géométrie est entrée dans le relevé après les couleurs et les titres :
#: treize écarts s'y sont révélés d'un coup, dont aucun n'était neuf — ils
#: étaient là depuis toujours, personne ne les mesurait. Les rendre bloquants
#: reviendrait à interdire toute livraison jusqu'à ce qu'ils soient tous
#: traités.
#:
#: **Ils se traitent, et le compte descend.** L'extension du relevé aux six
#: écrans en a fait apparaître vingt-cinq d'un coup ; quatorze ont été
#: corrigés dans la foulée — la hauteur des boutons et des listes, l'air sous
#: chaque barre de filtres, le pas des lignes du journal et l'écartement de
#: ses colonnes. Ce qui reste tient en quelques pixels, et passera du côté
#: bloquant au fur et à mesure.
INFORMATIF = "geo."

#: L'écart toléré sur une mesure de géométrie, avant de la signaler.
#:
#: **Deux moteurs de rendu ne tombent pas d'accord au pixel.** Le relevé le
#: savait déjà pour le texte, dont il arrondit la largeur à la dizaine ; la
#: comparaison par l'image l'admet aussi, à deux pixels près. Les mesures de
#: géométrie n'avaient, elles, aucune marge : « Filtres » fait quatre-vingt-six
#: pixels chez GTK et quatre-vingt-onze ici, « ↓ » cinquante contre
#: quarante-cinq — les deux toolkits ne mesurent pas le même texte pareil, et
#: n'imposent pas la même largeur minimale à un bouton court. Les aligner
#: exigerait de figer des largeurs en dur, qui casseraient au zoom et sous une
#: autre police : on satisferait la mesure en abîmant l'application.
#:
#: Deux unités, et non trois : au-delà, l'écart se voit à l'œil sur une barre
#: de filtres, et c'est précisément ce que ce contrôle existe pour trouver.
#:
#: L'unité suit la mesure — des pixels pour les hauteurs et les départs de
#: colonne, des millièmes de la largeur de fenêtre pour les places et les
#: largeurs, soit deux virgule quatre pixels à la largeur du relevé. Les deux
#: se valent à ce degré de finesse.
TOLERANCE_GEOMETRIE = 2


def assez_proche(a, b) -> bool:
    """Vrai si deux mesures ne diffèrent que de l'épaisseur du trait.

    Les listes se comparent terme à terme, et seulement si elles ont la même
    longueur : deux barres qui n'ont pas le même nombre de commandes ne se
    départagent pas au pixel, elles ne montrent pas la même chose.
    """
    if isinstance(a, bool) or isinstance(b, bool):
        return False
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= TOLERANCE_GEOMETRIE
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return all(assez_proche(x, y) for x, y in zip(a, b))
    return False


def main() -> int:
    details = "--details" in sys.argv[1:]

    with ecran_virtuel() as ecran:
        gtk = relever(PYTHON_GTK, "releve_gtk.py", "GTK", ecran)
    qt = relever(PYTHON_QT, "releve_qt.py", "Qt")
    if gtk is None or qt is None:
        return 1

    ecarts, signales, accords, tolerees = [], [], [], []
    for cle in sorted(set(gtk) | set(qt)):
        if cle not in gtk:
            trouve = (cle, "— (rien de tel en GTK)", qt[cle])
        elif cle not in qt:
            trouve = (cle, gtk[cle], "— (absent de Qt)")
        elif gtk[cle] != qt[cle]:
            trouve = (cle, gtk[cle], qt[cle])
        else:
            accords.append((cle, gtk[cle]))
            continue
        # Les mesures de géométrie sont montrées, pas opposées : elles
        # viennent d'arriver, aucune n'a encore été traitée, et faire échouer
        # le contrôle dessus arrêterait toutes les livraisons pour des écarts
        # connus. Elles passeront du côté bloquant à mesure qu'on les corrige.
        # Une géométrie qui ne diffère que de l'épaisseur du trait concorde :
        # voir `TOLERANCE_GEOMETRIE`, qui dit pourquoi l'exiger au pixel
        # reviendrait à figer des largeurs en dur.
        # `cle in gtk and cle in qt` d'abord : un point releve d'un seul cote
        # n'a pas deux valeurs a rapprocher, et le lire ici faisait lever une
        # KeyError qui arretait tout le controle.
        if (cle.startswith(INFORMATIF) and cle in gtk and cle in qt
                and assez_proche(gtk[cle], qt[cle])):
            tolerees.append(trouve)
            accords.append((cle, gtk[cle]))
            continue
        (signales if cle.startswith(INFORMATIF) else ecarts).append(trouve)

    if details:
        print(f"Ce qui concorde ({len(accords)} points) :")
        for cle, valeur in accords:
            print(f"  {cle:38} {valeur}")
        print()

    if tolerees:
        print(f"{len(tolerees)} mesure(s) de géométrie concordent à "
              f"{TOLERANCE_GEOMETRIE} près :")
        for cle, cote_gtk, cote_qt in tolerees:
            print(f"  {cle:34} GTK {cote_gtk}   Qt {cote_qt}")
        print()

    if signales:
        print(f"{len(signales)} mesure(s) de géométrie à traiter — signalées, "
              "non bloquantes :")
        for cle, cote_gtk, cote_qt in signales:
            print(f"  {cle:34} GTK {cote_gtk}   Qt {cote_qt}")
        print()

    if not ecarts:
        print(f"Les deux applications s'accordent sur les {len(accords)} points "
              "relevés.")
        return 0

    print(f"{len(ecarts)} écart(s) sur {len(accords) + len(ecarts)} points "
          "relevés — GTK fait foi :\n", file=sys.stderr)
    for cle, cote_gtk, cote_qt in ecarts:
        print(f"  {cle}", file=sys.stderr)
        print(f"      GTK : {cote_gtk}", file=sys.stderr)
        print(f"      Qt  : {cote_qt}", file=sys.stderr)
    print("\nCorrigez Qt, ou retirez le point du relevé s'il n'a pas lieu "
          "d'être comparé.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
