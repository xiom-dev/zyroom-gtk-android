#!/usr/bin/env python3
"""Prepare la version web de ZyRoom, `site-domaine/zyroom/`.

    python3 outils/page-zyroom.py

Des sorties ignorees par git, a deposer avec `index.html`, `zr.js`,
`travail.js`, `.htaccess` et `cache/.htaccess` :

- `zyroom.zip` : le code de ZyRoom-GTK qui ne touche pas a GTK (lecture de
  l'API, modeles, noms, categories, volumes, tris), ses donnees, la table
  des noms tiree du `string_client.pack`, et le pont `outils/zr_web.py`.
  Le Web Worker le deballe dans Pyodide.
- `zyroom.php` : `zyroom.modele.php` avec les cles API des guildes (La Lune
  et Rod of Heaven, lues dans les `guilds.ini` des applications), le sel des jetons et la liste des
  editeurs -- les memes que `mp.php`, pour qu'une connexion vaille pour les
  deux pages.
- `symboles/` et `polices/` : les images et la police de l'application.

**Pourquoi la table des noms vient du cache de l'application.** Le pack
appartient a l'installation du jeu ; ZyRoom en tire les noms une fois et les
garde en JSON. La page n'a pas de pack : elle prend ce JSON tel quel.
"""
from __future__ import annotations

import configparser
import json
import os
import re
import shutil
import sys
import zipfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSSIER = os.path.join(RACINE, "site-domaine", "zyroom")
MODELE = os.path.join(DOSSIER, "zyroom.modele.php")
PONT = os.path.join(RACINE, "outils", "zr_web.py")
PAQUET = os.path.join(RACINE, "zyroom-gtk", "zyroom")
SECRETS = os.path.expanduser("~/.config/zyroom")
#: Les guildes servies : La Lune Eternelle, et Rod of Heaven, celle des alts.
GUILDES = ("105906237", "105908280")

#: La table des noms, dans le cache de l'une des applications.
NOMS = (
    "~/.var/app/net.ryzom.zyroomgtk.dev/cache/zyroom-gtk/names.json",
    "~/.var/app/net.ryzom.zyroomgtk/cache/zyroom-gtk/names.json",
    "~/.cache/zyroom-gtk/names.json",
)
#: Ou trouver la cle de la guilde : les reglages des applications.
GUILDES_INI = (
    "~/.config/zyroom-gtk/guilds.ini",
    "~/.var/app/net.ryzom.zyroomgtk.dev/config/zyroom-gtk/guilds.ini",
    "~/.var/app/net.ryzom.zyroomgtk/config/zyroom-gtk/guilds.ini",
)
DATE = (2026, 1, 1, 0, 0, 0)


def premier(chemins) -> str:
    for chemin in chemins:
        chemin = os.path.expanduser(chemin)
        if os.path.isfile(chemin):
            return chemin
    raise SystemExit("Introuvable : " + ", ".join(chemins))


def sans_gtk(nom: str) -> bool:
    """Un module de l'application qui ne demande pas GTK."""
    with open(os.path.join(PAQUET, nom), encoding="utf-8") as fh:
        return not re.search(r"^\s*(from gi|import gi)", fh.read(), re.M)


def fabriquer_zip() -> None:
    archive = os.path.join(DOSSIER, "zyroom.zip")
    entrees = []
    for nom in sorted(os.listdir(PAQUET)):
        if nom.endswith(".py") and sans_gtk(nom):
            entrees.append((os.path.join(PAQUET, nom), "zyroom/" + nom))
    for nom in sorted(os.listdir(os.path.join(PAQUET, "data"))):
        entrees.append((os.path.join(PAQUET, "data", nom), "zyroom/data/" + nom))
    entrees.append((premier(NOMS), "names.json"))
    entrees.append((PONT, "zr_web.py"))
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for chemin, nom in entrees:
            info = zipfile.ZipInfo(nom, DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(chemin, "rb") as fh:
                z.writestr(info, fh.read())
    print(f"zyroom.zip : {len(entrees)} fichiers, {os.path.getsize(archive) // 1024} ko")


def fabriquer_php() -> None:
    # Chaque cle dans le premier guilds.ini qui la porte : la variante guilde
    # de l'application n'a que La Lune, la dev a les deux.
    cles = {}
    for chemin in GUILDES_INI:
        ini = configparser.ConfigParser()
        ini.read(os.path.expanduser(chemin), encoding="utf-8")
        for gid in GUILDES:
            if gid not in cles and ini.has_section(gid):
                cle = ini[gid].get("key", "").strip()
                if re.fullmatch(r"g[A-Za-z0-9]{40}", cle):
                    cles[gid] = cle
    manquent = [g for g in GUILDES if g not in cles]
    if manquent:
        raise SystemExit("Clé de guilde introuvable : " + ", ".join(manquent))
    with open(os.path.join(SECRETS, "mp.sel"), encoding="utf-8") as fh:
        sel = fh.read().strip()
    editeurs = []
    with open(os.path.join(SECRETS, "mp.motsdepasse"), encoding="utf-8") as fh:
        for ligne in fh:
            if ligne.strip() and not ligne.lstrip().startswith("#"):
                editeurs.append(ligne.partition(":")[0].strip())
    with open(MODELE, encoding="utf-8") as fh:
        modele = fh.read()
    for trou in ("__CLES__", "__SEL__", "__EDITEURS__"):
        if modele.count(trou) != 1:
            raise SystemExit(f"{MODELE} : {trou} attendu une fois")
    php = (modele.replace("__CLES__", json.dumps(cles)).replace("__SEL__", sel)
           .replace("__EDITEURS__", json.dumps(editeurs, ensure_ascii=False)))
    with open(os.path.join(DOSSIER, "zyroom.php"), "w", encoding="utf-8") as fh:
        fh.write(php)
    print(f"zyroom.php : {len(cles)} clés de guilde, éditeurs", ", ".join(editeurs))


def copier_images() -> None:
    """Les symboles de l'application (onglets, contenants, bourse) et la
    gothique du nom : la page les montre tels quels."""
    for dossier, motif in (("symboles", ".png"), ("polices", ".ttf"), ("cartes", ".webp")):
        cible = os.path.join(DOSSIER, dossier)
        os.makedirs(cible, exist_ok=True)
        for nom in sorted(os.listdir(os.path.join(PAQUET, dossier))):
            if nom.endswith(motif):
                shutil.copy2(os.path.join(PAQUET, dossier, nom), os.path.join(cible, nom))
    print("symboles/, polices/ et cartes/ recopiés")


def main() -> int:
    fabriquer_zip()
    fabriquer_php()
    copier_images()
    return 0


if __name__ == "__main__":
    sys.exit(main())
