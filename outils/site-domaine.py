#!/usr/bin/env python3
"""Fabrique la copie de la page de téléchargement pour un domaine à soi.

    ./outils/site-domaine.py            écrit dans site-domaine/
    ./outils/site-domaine.py DOSSIER    ailleurs

**Une seule page, deux adresses.** La page vit dans `pages/index.html`, d'où
`livraison.sh` la publie sur GitHub Pages. La recopier à la main pour un
second hébergement, c'est se condamner à corriger deux fois chaque phrase et
à en oublier une : la page a déjà annoncé la 0.60 quatorze livraisons durant,
faute d'un numéro recopié. Cet outil la *dérive* — même source, deux sorties.

**Ce qu'il change, et rien d'autre.** Les liens de téléchargement et l'adresse
du manifeste deviennent absolus, et pointent vers GitHub. Les archives, elles,
ne bougent pas : elles pèsent deux cents mégaoctets et le dépôt Flatpak compte
cinq mille deux cent trente-huit fichiers. C'est la première étape d'un
déménagement en trois temps, et la seule qui ne risque rien — les applications
déjà installées continuent d'interroger l'adresse qu'elles connaissent.

**Pourquoi cela marche.** GitHub Pages répond `Access-Control-Allow-Origin: *`
sur `version.json` : une page servie depuis un autre domaine a le droit de le
lire, et affiche donc les vrais numéros de version. Vérifié, sans quoi la page
aurait montré des points de suspension à la place de chaque version.

À relancer après chaque livraison qui touche la page. Le reste du temps, la
page dit d'elle-même ce qui est en ligne : elle lit le manifeste.
"""
from __future__ import annotations

import os
import re
import shutil
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = os.path.join(RACINE, "pages")

#: L'adresse où les archives restent servies, tant qu'elles n'ont pas déménagé.
BASE = "https://xiom-dev.github.io/zyroom-gtk-android/"

#: Ce qui reste local, parce qu'on l'emporte avec la page.
EMPORTE = ("apercus/",)


def absolu(page: str) -> str:
    """Rend absolus les liens qui pointaient à côté de la page."""

    def refaire(trouve: re.Match) -> str:
        attribut, cible = trouve.group(1), trouve.group(2)
        if (cible.startswith(("http://", "https://", "#", "mailto:", "data:"))
                or cible.startswith(EMPORTE)):
            return trouve.group(0)
        return f'{attribut}="{BASE}{cible}"'

    return re.sub(r'\b(href|src)="([^"]+)"', refaire, page)


#: Le durcissement minimal du site, depose a cote de la page.
#:
#: **Le HTTP en clair est le seul vrai trou.** Le reste est bon par defaut chez
#: Infomaniak : les repertoires ne se listent pas, le serveur n'annonce pas sa
#: version, et le HSTS est deja pose. Mais `http://xiom.be` repondait, et une
#: page servie en clair peut etre reecrite en chemin -- y compris ses liens de
#: telechargement, qui menent a des executables. La redirection ferme cela.
#:
#: Pas de `Content-Security-Policy` : la page porte un script en ligne -- celui
#: qui va lire les numeros de version -- et l'autoriser demanderait
#: `unsafe-inline`, ce qui vide la regle de sa substance. Mieux vaut pas de
#: politique qu'une politique qui ne protege de rien.
HTACCESS = """\
# Tout passe en HTTPS. Le certificat est la ; repondre en clair, c'est offrir
# a un intermediaire la possibilite de reecrire la page -- et ses liens de
# telechargement menent a des executables.
<IfModule mod_rewrite.c>
  RewriteEngine On
  RewriteCond %{HTTPS} !=on
  RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
</IfModule>

<IfModule mod_headers.c>
  # Le navigateur ne redevine pas le type d'un fichier : un .jpg reste une
  # image, quoi que son contenu evoque.
  Header always set X-Content-Type-Options "nosniff"
  # La page ne s'ouvre pas dans le cadre d'un autre site.
  Header always set X-Frame-Options "SAMEORIGIN"
  # On ne raconte pas d'ou vient le visiteur aux sites que l'on cite.
  Header always set Referrer-Policy "strict-origin-when-cross-origin"
</IfModule>

# Pas de liste des fichiers d'un dossier. Deja le cas chez Infomaniak ; ecrit
# ici pour que cela reste vrai si l'hebergement change un jour.
Options -Indexes
"""


def main() -> int:
    sortie = (sys.argv[1] if len(sys.argv) > 1
              else os.path.join(RACINE, "site-domaine"))
    source = os.path.join(PAGES, "index.html")
    if not os.path.isfile(source):
        print(f"Introuvable : {source}", file=sys.stderr)
        return 1

    page = absolu(open(source, encoding="utf-8").read())
    # Le manifeste se lit là où il est publié : la page n'en emporte pas de
    # copie, sinon elle annoncerait des numéros figés au jour de sa création.
    page = page.replace('fetch("version.json")', f'fetch("{BASE}version.json")')

    os.makedirs(sortie, exist_ok=True)
    open(os.path.join(sortie, "index.html"), "w", encoding="utf-8").write(page)
    apercus = os.path.join(sortie, "apercus")
    shutil.rmtree(apercus, ignore_errors=True)
    shutil.copytree(os.path.join(PAGES, "apercus"), apercus)
    open(os.path.join(sortie, ".htaccess"), "w",
         encoding="utf-8").write(HTACCESS)

    poids = sum(os.path.getsize(os.path.join(racine, f))
                for racine, _, fichiers in os.walk(sortie) for f in fichiers)
    combien = sum(len(f) for _, _, f in os.walk(sortie))
    print(f"  {sortie}")
    print(f"  {combien} fichiers, {poids / 1024:.0f} Ko")
    print()
    print("  À déposer tel quel à la racine web de l'hébergement Infomaniak")
    print("  (le dossier « web/ » ou « sites/<domaine>/ » selon la formule).")
    restants = len(re.findall(r'"' + re.escape(BASE), page))
    print(f"  {restants} liens pointent encore vers GitHub : c'est voulu, "
          "les\n  archives n'ont pas déménagé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
