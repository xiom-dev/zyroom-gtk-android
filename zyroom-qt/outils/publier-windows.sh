#!/usr/bin/env bash
#
# Depose le paquet Windows construit par la CI, et le dit au manifeste.
#
#   outils/publier-windows.sh          le dernier paquet construit
#   outils/publier-windows.sh 1.11.34  celui d'une version precise
#
# **Pourquoi ce script existe.** Le paquet Windows ne se construit pas ici : il
# sort d'une machine que GitHub prete le temps d'un tag `qt-*`, et le resultat
# attend en artefact. Le deposer etait un geste a la main, et un geste a la
# main s'oublie -- il l'a ete deux fois, chaque fois avec le meme effet : le
# manifeste annoncait une version que l'archive Windows ne contenait pas, et
# les joueurs de ce systeme tournaient en rond, reinstallant sans fin la meme
# vieille version.
#
# Ici, le paquet et la case du manifeste partent ensemble : on ne peut plus
# faire l'un sans l'autre.
set -euo pipefail

racine=$(cd "$(dirname "$0")/.." && pwd)
cd "$racine"
pages=$racine/../pages
manifeste=$pages/version.json
depot=xiom-dev/zyroom-gtk-android
servi=ZyRoom-Qt-windows.zip

command -v gh >/dev/null || {
    echo "Erreur : gh n'est pas installe -- c'est lui qui va chercher l'artefact." >&2
    exit 1
}

version=${1:-}
if [ -n "$version" ]; then
    execution=$(gh run list --repo "$depot" --workflow zyroom-qt-windows.yml \
        --limit 30 --json databaseId,headBranch,conclusion \
        -q "[.[] | select(.headBranch==\"qt-$version\" and .conclusion==\"success\")][0].databaseId")
else
    execution=$(gh run list --repo "$depot" --workflow zyroom-qt-windows.yml \
        --limit 10 --json databaseId,headBranch,conclusion \
        -q "[.[] | select(.conclusion==\"success\")][0].databaseId")
fi
[ -n "$execution" ] && [ "$execution" != "null" ] || {
    echo "Erreur : aucune construction Windows reussie${version:+ pour la $version}." >&2
    exit 1
}

travail=$(mktemp -d)
trap 'rm -rf "$travail"' EXIT
echo "── artefact de la construction $execution"
gh run download "$execution" --repo "$depot" --dir "$travail" >/dev/null

archive=$(find "$travail" -name "ZyRoom-Qt-*-windows.zip" ! -name "*chef*" | head -1)
[ -n "$archive" ] || { echo "Erreur : pas d'archive Windows dans l'artefact." >&2; exit 1; }
trouvee=$(basename "$archive" | sed -E 's/ZyRoom-Qt-(.*)-windows\.zip/\1/')

# Le paquet doit contenir ce qu'il annonce : une archive sans son executable
# n'a rien a faire sur la page de telechargement.
python3 - "$archive" <<'PY'
import sys, zipfile
noms = zipfile.ZipFile(sys.argv[1]).namelist()
attendus = ("ZyRoom-Qt/ZyRoom-Qt.exe", "ZyRoom-Qt/Installer.bat")
manquants = [n for n in attendus if n not in noms]
if manquants:
    raise SystemExit(f"Erreur : {', '.join(manquants)} absent(s) de l'archive.")
print(f"  {len(noms)} entrees, executable et installeur presents")
PY

cp "$archive" "$pages/$servi"
chef=$(find "$travail" -name "*windows-chef.zip" | head -1)
[ -n "$chef" ] && cp "$chef" "$racine/dist/"

# Le code de cette version : celui que le manifeste porte deja pour Linux si
# les numeros se suivent, sinon il faut le lire dans l'archive -- on prend
# celui de la racine, que la livraison vient d'ecrire.
python3 - "$manifeste" "$trouvee" <<'PY'
import json, sys
chemin, nom = sys.argv[1:3]
manifeste = json.load(open(chemin, encoding="utf-8"))
entree = manifeste["net.ryzom.zyroomqt"]
cases = entree.get("systemes") or {}
# Le code du paquet Windows est celui de la version qu'il porte : si c'est la
# derniere livree, c'est celui de la racine ; sinon on garde celui qu'on avait.
code = entree["versionCode"] if entree["versionName"] == nom else \
    cases.get("windows", {}).get("versionCode", 0)
cases["windows"] = {"versionCode": int(code), "versionName": nom}
entree["systemes"] = cases
json.dump(manifeste, open(chemin, "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
open(chemin, "a", encoding="utf-8").write("\n")
print(f"  version.json : windows -> {nom} (code {code})")
PY

echo "  pages/$servi depose"
cat <<'FIN'

  Reste a publier le site :

    cd ..
    tampon=$(mktemp -u)
    (cd pages && GIT_INDEX_FILE=$tampon git --git-dir=../.git --work-tree=. add -Af .)
    arbre=$(GIT_INDEX_FILE=$tampon git write-tree)
    commit=$(git commit-tree "$arbre" -m "Site : paquet Windows")
    git push -f origin "$commit:refs/heads/gh-pages"
FIN
