#!/usr/bin/env bash
#
# Livraison de ZyRoom-Qt, d'un seul geste.
#
#   ./livraison.sh              construit le numero actuel
#   ./livraison.sh 1.1          renumerote en 1.1, puis construit
#
# Ce que le script fait, dans l'ordre : recopier le numero la ou il s'affiche,
# verifier que le noyau n'est pas perime, construire, poser l'archive dans
# pages/ et l'annoncer dans version.json. **Rien n'est envoye sur GitHub** :
# il s'arrete au bord et affiche ce qui reste a pousser.
#
# **Le numero de version et le versionCode vont ensemble.** Le premier
# s'affiche, le second se compare -- et c'est lui, et lui seul, que la mise a
# jour regarde. Le script incremente le second a chaque livraison : oublier de
# le faire, c'est publier une version que personne ne verra jamais.
#
# **L'archive part avant le manifeste, dans le meme commit.** Si version.json
# annoncait un numero neuf sans que l'archive soit en ligne, le bouton
# "Mettre a jour" menerait a une adresse morte -- et il n'y a pas de retour en
# arriere : l'application aurait deja dit a son utilisateur qu'une version
# l'attend.
#
# **Ce script ne construit que pour Linux.** Le paquet Windows se construit
# sur une machine Windows, avec packaging\build.bat, et se depose a la main
# dans pages/ sous le nom que version.json annonce.
set -euo pipefail

# Sans cela, un __init__.py reecrit dans la meme seconde garde son .pyc
# et la construction embarque le numero de version precedent.
export PYTHONDONTWRITEBYTECODE=1

racine=$(cd "$(dirname "$0")" && pwd)
cd "$racine"

pages=$racine/../pages
manifeste=$pages/version.json
init=$racine/zyroom/__init__.py
application=net.ryzom.zyroomqt
base_url=https://xiom-dev.github.io/zyroom-gtk-android
python=${PYTHON:-$racine/.venv/bin/python}

[ -x "$python" ] || { echo "Environnement virtuel introuvable." >&2; exit 1; }
[ -d "$pages" ] || {
    echo "Erreur : $pages absent." >&2
    echo "Recuperez la branche gh-pages dans ../pages/ avant de livrer," >&2
    echo "sinon version.json serait reecrit a partir de rien." >&2
    exit 1
}

# --------------------------------------------------------------- Numero
nom_actuel=$("$python" -c "import zyroom; print(zyroom.__version__)")
code_actuel=$("$python" -c "import zyroom; print(zyroom.__version_code__)")
nom=${1:-$nom_actuel}
code=$((code_actuel + 1))

echo "== Version =="
echo "  nom          : $nom_actuel -> $nom"
echo "  versionCode  : $code_actuel -> $code"

"$python" - "$init" "$nom" "$code" <<'PY'
import re, sys
chemin, nom, code = sys.argv[1], sys.argv[2], sys.argv[3]
with open(chemin, encoding="utf-8") as fh:
    texte = fh.read()
texte = re.sub(r'__version__ = "[^"]*"', f'__version__ = "{nom}"', texte)
texte = re.sub(r"__version_code__ = \d+", f"__version_code__ = {code}", texte)
with open(chemin, "w", encoding="utf-8") as fh:
    fh.write(texte)
PY

# ---------------------------------------------------------- Construction
echo
echo "== Noyau =="
outils/sync-noyau.sh --verifie

# L'aspect, confronte a celui de la version GTK, qui fait foi.
#
# Tous les ecarts trouves jusqu'ici l'ont ete a l'oeil, apres livraison : une
# jauge etiree sur toute la hauteur d'une rangee, une ligne de saison en gras,
# un vert a un point du bon, un bouton qui ne s'allumait pas. Chacun se voyait
# pourtant dans une mesure. La livraison s'arrete donc ici, tant qu'un point
# differe -- corriger apres coup demande une version de plus, et c'est le
# joueur qui la subit.
echo
echo "== Parite avec GTK, point par point =="
outils/parite.py

# Et l'aspect par l'image, parce que le releve point par point ne voit que ce
# qu'on pense a lui demander. Celui-ci photographie les deux fenetres sur un
# serveur X virtuel et confronte leurs bandes et leurs couleurs : il a trouve
# seul un bandeau du bas trop mince, des boutons sans cadre, des icones non
# recolorees, des onglets peints du mauvais gris et un trait de separation
# absent -- tous invisibles au releve, et tous bien reels a l'ecran.
#
# Il prend une quarantaine de secondes : le temps de poser deux fenetres et de
# les photographier. C'est le prix d'une livraison qui ne fait pas decouvrir
# l'ecart au joueur.
echo
echo "== Parite avec GTK, par l'image =="
outils/parite-image.py

echo
echo "== Construction =="
packaging/build.sh >/dev/null

# L'archive est nommee, pas devinee. `ls -t | head -1` prenait la plus recente
# de dist/ : depuis que paquet-chef.sh sait construire pour Linux, une archive
# du chef fabriquee entre-temps serait partie vers la page publique -- et avec
# elle le lanceur qui devoile les coffres reserves. Le nom exact ferme cette
# porte, et l'absence du fichier arrete la livraison au lieu de la detourner.
archive="dist/ZyRoom-Qt-${nom}-linux-$(uname -m).zip"
[ -f "$archive" ] || {
    echo "Erreur : $archive introuvable apres la construction." >&2
    exit 1
}
echo "  $archive  ($(du -h "$archive" | cut -f1))"

# ------------------------------------------------------------ Publication
# Un nom fixe, que version.json annonce une fois pour toutes : une adresse qui
# changerait a chaque livraison obligerait a reecrire le manifeste et l'index
# ensemble, et le moindre oubli casserait le telechargement.
servi=ZyRoom-Qt-linux.zip
cp "$archive" "$pages/$servi"
echo
echo "== Publication =="
echo "  $pages/$servi"

# La copie datee : c'est l'archive locale de ce qui est parti, la seule facon
# de retrouver le paquet d'un numero donne une fois la page ecrasee.
cp "$archive" "dist/ZyRoom-Qt-${nom}-linux.zip"

"$python" - "$manifeste" "$application" "$code" "$nom" "$base_url" "$servi" <<'PY'
import json, sys
chemin, application, code, nom, base, servi = sys.argv[1:7]
with open(chemin, encoding="utf-8") as fh:
    manifeste = json.load(fh)
entree = manifeste.get(application, {})
entree["versionCode"] = int(code)
entree["versionName"] = nom
# **Et le meme numero dans la case de ce systeme-la.** La racine dit ce qui a
# ete livre en dernier, quel que soit le systeme ; les cases disent ce que
# chacun a reellement en ligne. Sans elles, une version Windows en retard ne se
# contentait pas d'etre en retard : elle se croyait perpetuellement a mettre a
# jour, telechargeait une archive plus ancienne que ce que la racine annoncait,
# et recommencait. La racine reste ecrite : les versions deja installees ne
# connaissent qu'elle.
systemes = entree.get("systemes") or {}
systemes["linux"] = {"versionCode": int(code), "versionName": nom}
entree["systemes"] = systemes
# Une adresse par systeme : un bundle Linux ne se lance pas sous Windows.
# Celle de Windows est conservee telle quelle -- ce script ne la construit
# pas, et l'ecraser effacerait une livraison faite depuis l'autre machine.
urls = entree.get("urls") or {}
urls["linux"] = f"{base}/{servi}"
urls.setdefault("windows", f"{base}/ZyRoom-Qt-windows.zip")
entree["urls"] = urls
manifeste[application] = entree
with open(chemin, "w", encoding="utf-8") as fh:
    json.dump(manifeste, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
print(f"  version.json : {application} -> {nom} (code {code})")
PY

# **L'archive Windows a-t-elle suivi ?** Elle ne se construit pas ici, et il
# est arrive deux fois qu'on livre plusieurs versions sans la deposer : les
# joueurs de ce systeme-la tournaient alors en rond. Le manifeste sait
# desormais ce que Windows a en ligne, et l'on regarde s'il a decroche.
python3 - "$manifeste" <<'PY'
import json, sys
manifeste = json.load(open(sys.argv[1], encoding="utf-8"))
entree = manifeste.get("net.ryzom.zyroomqt", {})
cases = entree.get("systemes") or {}
# La racine, et non la case de Linux : elle porte toujours ce qu'on vient de
# livrer, meme la premiere fois -- quand aucune case n'existe encore.
ici = entree.get("versionCode", 0)
la_bas = cases.get("windows", {}).get("versionCode")
if la_bas is None:
    print("\n  ⚠ Le manifeste ne dit pas ce que Windows a en ligne.")
    print("    Deposez son paquet avec outils/publier-windows.sh.")
elif la_bas < ici:
    print(f"\n  ⚠ Windows est reste a la {cases['windows']['versionName']}, "
          f"nous livrons la {cases['linux']['versionName']}.")
    print("    Ses joueurs ne verront rien de neuf tant que son paquet n'est")
    print("    pas depose : outils/publier-windows.sh")
PY

cat <<'FINAL'

Reste a faire, a la main -- rien n'a ete envoye :

  1. le paquet Windows, s'il change lui aussi : le construire la-bas avec
     packaging\build.bat, et deposer son ZIP dans pages/ sous le nom
     ZyRoom-Qt-windows.zip. Le manifeste l'annonce deja.

  2. publier le site (version.json et l'archive qu'il annonce) :

       cd ..
       tampon=$(mktemp -u)
       (cd pages && GIT_INDEX_FILE=$tampon git --git-dir=../.git --work-tree=. add -Af .)
       arbre=$(GIT_INDEX_FILE=$tampon git write-tree)
       commit=$(git commit-tree "$arbre" -m "Site : ZyRoom-Qt et version.json")
       git push -f origin "$commit:refs/heads/gh-pages"

     Une branche orpheline reconstruite a chaque fois, sans changer de branche
     ici : le contenu de pages/ est ignore sur main.

  3. valider le nouveau numero et etiqueter :

       git add -u && git commit
       git tag qt-VERSION
       git push origin main --follow-tags

     L'etiquette dit quel code a produit quelle archive : sans elle,
     retrouver la version qu'un joueur execute devient une fouille.

FINAL
