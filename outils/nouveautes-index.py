#!/usr/bin/env python3
"""Écrit la colonne « Nouveautés » du sommaire https://xiom.be/index/.

Les changements du site sont dans outils/nouveautes-site.json, le plus récent
en tête (tout l'historique y reste) ; la page n'en montre que les NOMBRE
premiers, entre les marques NOUVEAUTES de site-domaine/index/page.html.

    python3 outils/nouveautes-index.py                     réécrit la colonne
    python3 outils/nouveautes-index.py ajouter "Texte."    ajoute en tête, daté du jour

Puis déposer site-domaine/index/page.html.
"""

import datetime
import html
import json
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LISTE = os.path.join(RACINE, "outils", "nouveautes-site.json")
PAGE = os.path.join(RACINE, "site-domaine", "index", "page.html")
NOMBRE = 10
DEBUT, FIN = "    <!-- NOUVEAUTES -->\n", "    <!-- /NOUVEAUTES -->"


def lire():
    with open(LISTE, encoding="utf-8") as f:
        return json.load(f)


def texte_html(texte):
    """Le texte, avec en gras (en or sur la page) ce qui precede le premier
    « : », la partie du site concernee (« Guerre d'OP : ... »)."""
    sujet, deux_points, reste = texte.partition(" : ")
    if not deux_points:
        return html.escape(texte, quote=False)
    return f"<b>{html.escape(sujet, quote=False)}</b> : {html.escape(reste, quote=False)}"


def ecrire_page(liste):
    with open(PAGE, encoding="utf-8") as f:
        page = f.read()
    if page.count(DEBUT) != 1 or page.count(FIN) != 1:
        sys.exit(f"{PAGE} : marques {DEBUT.strip()} et {FIN.strip()} introuvables")
    lignes = "".join(
        f'    <li><time datetime="{n["date"]}">{datetime.date.fromisoformat(n["date"]).strftime("%d/%m")}</time>'
        f'{texte_html(n["texte"])}</li>\n' for n in liste[:NOMBRE])
    avant, reste = page.split(DEBUT)
    apres = reste.split(FIN, 1)[1]
    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(avant + DEBUT + lignes + FIN + apres)
    print(f"page.html : {min(NOMBRE, len(liste))} nouveautés, la plus récente : {liste[0]['texte']}")


def main():
    liste = lire()
    if sys.argv[1:2] == ["ajouter"]:
        texte = " ".join(sys.argv[2:]).strip()
        if not texte:
            sys.exit('Usage : nouveautes-index.py ajouter "Texte de la nouveauté."')
        liste.insert(0, {"date": datetime.date.today().isoformat(), "texte": texte})
        with open(LISTE, "w", encoding="utf-8") as f:
            json.dump(liste, f, ensure_ascii=False, indent=1)
            f.write("\n")
    elif sys.argv[1:]:
        sys.exit(__doc__)
    ecrire_page(liste)


if __name__ == "__main__":
    main()
