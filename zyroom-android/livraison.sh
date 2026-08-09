#!/usr/bin/env bash
#
# Livraison d'un APK Android, d'un seul geste.
#
#   ./livraison.sh dev          → variante du mainteneur, numéro d'affichage inchangé
#   ./livraison.sh guilde 0.4   → variante des joueurs, renumérotée 0.4
#   ./livraison.sh tout 0.4     → les deux
#
# Pourquoi un script plutôt qu'une note dans le README : une livraison doit
# tenir quatre choses d'accord — le versionCode de l'APK, son nom de fichier, le
# versionCode publié dans version.json et l'URL qu'il annonce. Oublier le
# premier ne casse rien de visible : l'APK s'installe, se lance, et *aucun
# téléphone ne verra jamais la mise à jour*, parce que versionCode est le seul
# numéro qu'Android compare. C'est la panne qu'on ne remarque pas. Ici le numéro
# croît toujours, et par construction plus haut que celui qui est en ligne.
#
# Rien n'est envoyé sur GitHub : le script s'arrête au bord et affiche ce qui
# reste à pousser.
set -euo pipefail

racine=$(cd "$(dirname "$0")" && pwd)
cd "$racine"

manifeste=$racine/../pages/version.json
proprietes=$racine/version.properties

usage() {
    sed -n '3,7p' "$0" | sed 's/^# \?//'
    exit 2
}

case ${1:-} in
    guilde|dev) variantes=("$1") ;;
    tout)       variantes=(guilde dev) ;;
    *)          usage ;;
esac
nom_demande=${2:-}

# Garde-fous : mieux vaut refuser tôt que livrer à moitié.
[ -f "$manifeste" ] || {
    echo "Erreur : $manifeste introuvable." >&2
    echo "Le site de mises à jour n'est pas dans cet arbre — récupère la branche" >&2
    echo "gh-pages dans ../pages/ avant de livrer, sinon version.json ne serait" >&2
    echo "pas mis à jour et personne ne verrait la nouvelle version." >&2
    exit 1
}
[ -f "$racine/keystore.properties" ] || {
    echo "Erreur : keystore.properties absent — l'APK sortirait non signé," >&2
    echo "donc ni installable par-dessus l'ancien, ni reconnu comme venant de toi." >&2
    exit 1
}
command -v jq >/dev/null || { echo "Erreur : jq est nécessaire (apt install jq)." >&2; exit 1; }

export ANDROID_HOME=${ANDROID_HOME:-$HOME/Android/Sdk}

lire()   { grep -E "^$1=" "$proprietes" | head -1 | cut -d= -f2 | tr -d '[:space:]'; }
ecrire() {
    grep -qE "^$1=" "$proprietes" || { echo "clé $1 absente de $proprietes" >&2; exit 1; }
    sed -i -E "s|^$1=.*|$1=$2|" "$proprietes"
}
publie() { jq -r --arg p "$1" '.[$p].versionCode // 0' "$manifeste"; }

paquet_de() { case $1 in guilde) echo net.ryzom.zyroom ;; dev) echo net.ryzom.zyroom.dev ;; esac; }

# Numérotation : on part du plus haut des deux numéros connus — celui du dépôt
# et celui réellement publié. Le second peut être devant si une livraison est
# partie d'un autre poste ; s'en tenir au dépôt produirait alors un APK
# qu'aucun téléphone n'accepterait comme plus récent.
declare -A codes noms
for v in "${variantes[@]}"; do
    paquet=$(paquet_de "$v")
    local_code=$(lire "$v.versionCode")
    en_ligne=$(publie "$paquet")
    codes[$v]=$(( (local_code > en_ligne ? local_code : en_ligne) + 1 ))
    noms[$v]=${nom_demande:-$(lire "$v.versionName")}
    printf '%-7s versionCode %s → %s   version %s\n' \
        "$v" "$local_code (en ligne : $en_ligne)" "${codes[$v]}" "${noms[$v]}"
done

for v in "${variantes[@]}"; do
    ecrire "$v.versionCode" "${codes[$v]}"
    ecrire "$v.versionName" "${noms[$v]}"
done

taches=()
for v in "${variantes[@]}"; do
    taches+=("assemble${v^}Release")
done
echo
./gradlew --quiet "${taches[@]}"

mkdir -p "$racine/dist"
for v in "${variantes[@]}"; do
    paquet=$(paquet_de "$v")
    nom=${noms[$v]}
    construit=$racine/app/build/outputs/apk/$v/release/app-$v-release.apk
    [ -f "$construit" ] || { echo "Erreur : $construit absent après la construction." >&2; exit 1; }

    # Pas de parenthèses dans les noms de fichiers : GitHub les réécrit en
    # points sur les pièces jointes des Releases, et les empreintes publiées ne
    # correspondent plus aux noms servis.
    # Les deux variantes sont servies depuis la page, sous un nom fixe que
    # version.json annonce une fois pour toutes. Une Release GitHub ferait
    # aussi bien pour le joueur, mais elle demande un jeton d'API : la
    # publication cesserait d'être faisable d'un seul geste, et il faudrait
    # que la Release existe *avant* que version.json l'annonce, sinon les
    # téléphones verraient un numéro neuf et un téléchargement mort.
    # La copie datée dans dist/ reste, elle, ce qu'on joint à une Release.
    case $v in
        guilde)
            fichier=V-RyLune-Android_$nom.apk
            affiche=$nom
            servi=V-RyLune-Android.apk
            ;;
        dev)
            fichier=V-RyLune-Android-dev_$nom.apk
            affiche=$nom-dev          # ce que l'APK annonce vraiment : versionNameSuffix
            servi=V-RyLune-Android-dev.apk
            ;;
    esac
    url=https://xiom-dev.github.io/zyroom-gtk-android/$servi
    cp "$construit" "$racine/../pages/$servi"
    cp "$construit" "$racine/dist/$fichier"

    tampon=$(mktemp)
    jq --arg p "$paquet" --argjson c "${codes[$v]}" --arg n "$affiche" --arg u "$url" \
       '.[$p] = {versionCode: $c, versionName: $n, url: $u}' "$manifeste" > "$tampon"
    mv "$tampon" "$manifeste"

    echo
    echo "$fichier"
    (cd "$racine/dist" && sha256sum "$fichier")
    apksigner=$(ls "$ANDROID_HOME"/build-tools/*/apksigner 2>/dev/null | tail -1 || true)
    if [ -n "$apksigner" ]; then
        "$apksigner" verify --print-certs "$racine/dist/$fichier" \
            | grep -E 'Signer #1 certificate DN' || echo "  signature NON vérifiable" >&2
    fi
done

cat <<'FIN'

Reste à faire, à la main — rien n'a été envoyé :

  1. publier le site (version.json, et l'APK dev qu'il annonce) :

       cd ..
       tampon=$(mktemp -u)
       (cd pages && GIT_INDEX_FILE=$tampon git --git-dir=../.git --work-tree=. add -Af .)
       arbre=$(GIT_INDEX_FILE=$tampon git write-tree)
       commit=$(git commit-tree "$arbre" -m "Site : dépôt Flatpak et version.json")
       git push -f origin "$commit:refs/heads/gh-pages"

     Une branche orpheline reconstruite à chaque fois, sans changer de branche
     ici : le contenu de pages/ est ignoré sur main, et un `git checkout` l'a
     déjà effacé une fois.

  2. valider le nouveau numéro : git add -u && git commit
  3. variante guilde seulement : créer la Release GitHub et y joindre
     l'APK de dist/, puis vérifier que l'URL annoncée par version.json répond.
FIN
