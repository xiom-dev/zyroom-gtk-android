#!/usr/bin/env python3
"""Relève au tracker la fourchette d'humidité de chaque gisement.

C'est **la** donnée qui dit quand une matière sort : le jeu range l'humidité en
quatre bandes, et chaque gisement en occupe exactement deux.

    0 – 16,6 %    condition Excellente
    16,7 – 49,9 % condition Bonne
    50 – 83,3 %   condition Mauvaise
    83,4 – 100 %  condition Exécrable

Sec vaut mieux qu'humide, contrairement à ce qu'on croirait : c'est mesuré sur
l'API du jeu, quarante et un cycles sans une exception.

Le relevé remplace le classeur de la guilde, qui donnait ces conditions de
mémoire et se trompait sur quarante-cinq matières sur quarante-six.

    python3 outils/humidites.py            # tout relever
    python3 outils/humidites.py --limite 6 # un essai

**Le jeton reste dehors.** Comme pour les cartes, l'empreinte est lue dans
`~/.config/zyroom/atys.url`, hors du dépôt, et un garde-fou vérifie avant
écriture qu'elle ne s'est glissée dans aucune sortie.

Attribution : tracker de Tgwaste sur atys.us, données de gisements de
ballisticmystix.net.
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cartes_gisements import (QUALITES, catalogue, empreinte,  # noqa: E402
                              fiche, sans_jeton)

SORTIE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "donnees", "humidites-gisements.json")

SOURCE = ("Relevé des fourchettes d'humidité, une par gisement, extrait des "
          "fiches du tracker d'atys.us (Tgwaste) — données de gisements de "
          "ballisticmystix.net.")
POURQUOI = ("Le tracker ne se consulte qu'avec le jeton personnel de Xiom, qui "
            "ne doit pas entrer dans le dépôt. Le relevé est donc figé ici "
            "plutôt que refait à chaque fabrication : relancer "
            "outils/humidites.py pour le rafraîchir.")


def main() -> int:
    options = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    options.add_argument("--url", default="", help="adresse du tracker")
    options.add_argument("--pause", type=float, default=1.0,
                         help="secondes entre deux requêtes (défaut : 1)")
    options.add_argument("--limite", type=int, default=0,
                         help="s'arrêter après N fiches, pour un essai")
    options.add_argument("--sortie", default=SORTIE)
    reglages = options.parse_args()

    cle = empreinte(reglages.url)
    print(f"empreinte lue, {len(cle)} caractères — elle ne sera pas écrite\n")

    print("catalogue des matières :")
    couples = catalogue(cle, reglages.pause)
    print(f"→ {len(couples)} couples famille/matière\n")

    fiches = [(q, f, m) for f, m in couples for q in QUALITES]
    if reglages.limite:
        fiches = fiches[:reglages.limite]

    humidites, vides = {}, []
    for rang, (qualite, famille, matiere) in enumerate(fiches, 1):
        plages, _cartes = fiche(cle, famille, matiere, qualite, reglages.pause)
        if plages:
            humidites[f"{qualite}|{famille}|{matiere}"] = plages
        else:
            vides.append(f"{qualite}|{famille}|{matiere}")
        print(f"  [{rang:3d}/{len(fiches)}] {qualite:9s} {famille}/{matiere} "
              f"→ {plages or 'aucune fourchette'}", flush=True)

    # Une matière sans fourchette n'existe pas dans cette qualité : c'est ainsi
    # que le site sépare les suprêmes des seules excellentes, il ne le dit
    # nulle part autrement.
    ancien = {}
    if os.path.exists(reglages.sortie):
        with open(reglages.sortie, encoding="utf-8") as fh:
            ancien = json.load(fh).get("humidites", {})
    perdues = sorted(set(ancien) - set(humidites))
    if perdues:
        print(f"\n{len(perdues)} fourchette(s) que le site ne donne plus : "
              f"{perdues}", file=sys.stderr)
        raise SystemExit("relevé refusé : on ne remplace pas des données "
                         "connues par un trou")

    contenu = {
        "_source": SOURCE,
        "_pourquoi_ici": POURQUOI,
        "_releve_le": time.strftime("%Y-%m-%d"),
        "humidites": dict(sorted(humidites.items())),
    }
    texte = sans_jeton(json.dumps(contenu, ensure_ascii=False, indent=2), cle)
    with open(reglages.sortie, "w", encoding="utf-8") as fh:
        fh.write(texte + "\n")

    nouvelles = sorted(set(humidites) - set(ancien))
    print(f"\n{len(humidites)} fourchettes écrites dans {reglages.sortie}")
    if nouvelles:
        print(f"{len(nouvelles)} nouvelle(s) : {nouvelles}")
    print(f"{len(vides)} couple(s) sans fourchette — inexistants dans cette "
          f"qualité")
    print("écrit sans l'empreinte, vérifié")
    return 0


if __name__ == "__main__":
    sys.exit(main())
