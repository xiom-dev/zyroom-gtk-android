#!/usr/bin/env python3
"""Fabrique `site-domaine/OP/releve.php` à partir de son modèle.

Le modèle (`releve.modele.php`) est versionné **sans aucun secret**. Cet outil
y met les empreintes bcrypt des mots de passe de xiom.be (`outils/acces.py` :
les six codes personnels et le mot de passe commun) et le sel qui signe les
jetons, gardé hors du dépôt dans `~/.config/zyroom/`. Le `releve.php` produit est ignoré par git : c'est lui, et lui seul,
qu'on dépose sur xiom.be avec `index.html` et `.htaccess`.

    python3 outils/page-op.py

Changer un mot de passe : voir `outils/acces.py`, relancer, redéposer
`releve.php`. Les jetons déjà donnés restent valables jusqu'à leur
terme (trente jours) ; pour les révoquer tous, tirer aussi un nouveau sel.
"""
import os
import sys

import acces

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSSIER = os.path.join(RACINE, "site-domaine", "OP")
MODELE = os.path.join(DOSSIER, "releve.modele.php")
CIBLE = os.path.join(DOSSIER, "releve.php")
SECRETS = os.path.expanduser("~/.config/zyroom")
SEL = os.path.join(SECRETS, "op.sel")


def lire(chemin: str, aide: str) -> str:
    if not os.path.isfile(chemin):
        raise SystemExit(f"Absent : {chemin}\n{aide}")
    with open(chemin, encoding="utf-8") as fh:
        return fh.read().strip()


def main() -> int:
    sel = lire(SEL, "En tirer un : python3 -c \"import secrets; "
                    "print(secrets.token_hex(24))\" > " + SEL)
    with open(MODELE, encoding="utf-8") as fh:
        modele = fh.read()
    for trou in ("__EMPREINTES__", "__VERIFIE__", "__SEL__"):
        if modele.count(trou) != 1:
            raise SystemExit(f"{MODELE} : {trou} attendu une fois")
    php = (modele.replace("__EMPREINTES__", acces.php_empreintes())
           .replace("__VERIFIE__", acces.PHP_VERIFIE).replace("__SEL__", sel))
    with open(CIBLE, "w", encoding="utf-8") as fh:
        fh.write(php)
    print("→", CIBLE)
    print("à déposer dans OP/ sur xiom.be : index.html, releve.php, .htaccess")
    return 0


if __name__ == "__main__":
    sys.exit(main())
