#!/usr/bin/env python3
"""Écrit le garde de la page https://xiom.be/padui/ (site-domaine/padui/garde.php).

La page s'ouvre avec les mots de passe de tout le site (outils/acces.py) :
le code personnel des six joueurs de confiance, ou le mot de passe commun.
garde.php n'en garde que les empreintes bcrypt, et le secret qui signe le
cookie d'entrée — comme le relevé du forage (forage/releve.php).

Les codes personnels des joueurs autorisés à déposer leurs drapeaux
(deposer.php) vivent dans ~/.config/zyroom/padui.deposants ; garde.php n'en
garde que les empreintes. --nouveau-code NOM en tire un autre pour ce joueur.
Le script écrit aussi padui/filtre.json, le tri des dépôts.

Changer un mot de passe : voir outils/acces.py, puis relancer ce script et
déposer garde.php. Il y recopie aussi la clef d'écriture du forage
(~/.config/zyroom/forage.cle), qui permet à ZyRoom-GTK de déposer les
drapeaux partagés. Les cookies déjà donnés restent valides 30 jours, sauf si le
secret change : ajouter --nouveau-secret pour fermer la porte à tout le monde.

    python3 outils/page-padui.py [--nouveau-secret]
"""

import json
import os
import re
import secrets
import sys

import acces
import bcrypt

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GARDE = os.path.join(RACINE, "site-domaine", "padui", "garde.php")
SECRETS = os.path.expanduser("~/.config/zyroom")
# La clef d'ecriture du releve du forage : la meme sert a ZyRoom-GTK (dev) pour
# deposer les drapeaux partages de Xiom (donnees.php).
CLE_FORAGE = os.path.join(SECRETS, "forage.cle")
# Les joueurs autorises a deposer leurs drapeaux (padui/deposer.php), chacun
# avec son code personnel : {nom: code}, en clair ici seulement (droits 600).
DEPOSANTS = os.path.join(SECRETS, "padui.deposants")
NOMS_DEPOSANTS = ("Xiom", "Yamaa", "Yzatis", "Thysela", "Arudy", "Azileth", "Nizyros", "Luz", "Ciboulette", "Cibou", "Deborat")
# Le filtre des depots : quelles matieres et quels rois/nommes reconnaitre,
# tire des donnees de l'installateur PadUI (le meme tri que lui).
INSTALLATEUR = os.path.expanduser("~/jeu/ryzom/padui-installeur")
FILTRE = os.path.join(RACINE, "site-domaine", "padui", "filtre.json")
# Comme les mots de passe de la page mp : douze lettres et chiffres melanges.
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"


def codes() -> dict:
    """Les codes des deposants : un tire pour chaque nouveau nom, les autres
    gardes. Retirer un nom de NOMS_DEPOSANTS lui retire le droit ;
    --nouveau-code NOM lui en tire un autre."""
    try:
        with open(DEPOSANTS, encoding="utf-8") as f:
            anciens = json.load(f)
    except (OSError, ValueError):
        anciens = {}
    if "--nouveau-code" in sys.argv:
        anciens.pop(sys.argv[sys.argv.index("--nouveau-code") + 1], None)
    sortie = {nom: anciens.get(nom) or "".join(secrets.choice(ALPHABET) for _ in range(16))
              for nom in NOMS_DEPOSANTS}
    with open(os.open(DEPOSANTS, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as f:
        json.dump(sortie, f, ensure_ascii=False, indent=1)
    return sortie


def filtre() -> None:
    """padui/filtre.json : les mots qui font d'un drapeau un drapeau de forage
    (dans les Primes) ou de roi/nomme (partout), comme l'installateur."""
    sys.path.insert(0, INSTALLATEUR)
    from padui_installeur import moteur
    dossier = os.path.join(INSTALLATEUR, "paquet")
    matieres = sorted({moteur._sans_accent(m) for m in moteur._charge(dossier, "gisements.json")}
                      | set(moteur.ALIAS))
    mobs = sorted({moteur._sans_accent(m) for m in moteur._charge(dossier, "catalogue.json")})
    with open(FILTRE, "w", encoding="utf-8") as f:
        json.dump({"primes": list(moteur.PRIMES), "matieres": matieres, "mobs": mobs,
                   "doublon": moteur.DOUBLON}, f, ensure_ascii=False)


def main() -> int:
    os.makedirs(SECRETS, exist_ok=True)
    # Le secret du cookie : gardé d'une fois sur l'autre, sauf demande.
    sel = None
    if os.path.isfile(GARDE) and "--nouveau-secret" not in sys.argv:
        m = re.search(r"const SEL = '([0-9a-f]+)';", open(GARDE, encoding="utf-8").read())
        sel = m.group(1) if m else None
    sel = sel or secrets.token_hex(24)
    with open(CLE_FORAGE, encoding="utf-8") as f:
        cle_forage = f.read().strip()
    deposants = codes()
    filtre()
    # PHP lit les empreintes $2y$, bcrypt en Python rend $2b$ : même calcul.
    empreintes = ",\n".join("    '%s' => '$2y$%s'" % (nom, bcrypt.hashpw(code.encode(), bcrypt.gensalt(12)).decode()[4:])
                            for nom, code in deposants.items())
    # La page : les six codes personnels ou le mot de passe commun (acces.py).
    empreinte_page = acces.php_empreintes()
    php = f"""<?php
// Le garde de https://xiom.be/padui/ : ecrit par outils/page-padui.py, ne pas
// modifier a la main. Inclus par donnees.php, deposer.php et restaurer.php ;
// la page elle-meme passe par la porte de xiom.be (index/porte.php).
//
// Les empreintes de ce qui ouvre la mise a jour des drapeaux de
// l'installateur (donnees.php) : les six codes personnels et le mot de passe
// commun (outils/acces.py). Et le secret des pages a code. Aucun mot de passe
// en clair n'est monte ici.
declare(strict_types=1);
const EMPREINTES = {empreinte_page};
const SEL = '{sel}';
// La clef d'ecriture du releve du forage (forage/releve.php) : elle seule peut
// deposer les drapeaux partages (donnees.php).
const CLE_FORAGE = '{cle_forage}';
// Les joueurs qui peuvent deposer leurs drapeaux (deposer.php), et
// l'empreinte de leur code personnel.
const DEPOSANTS = [
{empreintes},
];
"""
    php += "\n" + acces.PHP_VERIFIE
    with open(GARDE, "w", encoding="utf-8") as f:
        f.write(php)
    print(f"{GARDE} écrit (codes et mot de passe commun : outils/acces.py)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
