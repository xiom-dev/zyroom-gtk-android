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

apksigner=$(ls "$ANDROID_HOME"/build-tools/*/apksigner 2>/dev/null | tail -1 || true)
aapt2=$(ls "$ANDROID_HOME"/build-tools/*/aapt2 2>/dev/null | tail -1 || true)
[ -n "$apksigner" ] && [ -n "$aapt2" ] || {
    echo "Erreur : apksigner ou aapt2 introuvable sous $ANDROID_HOME/build-tools." >&2
    echo "Ils ne servent pas a construire mais a relire l'APK construit ; sans eux" >&2
    echo "la livraison partirait sans que rien n'ait verifie ce qui part." >&2
    exit 1
}

# L'empreinte de la cle qui signe V-RyLune depuis la premiere version.
#
# Android n'accepte une mise a jour que si elle porte la meme signature que
# l'application deja installee. Un APK signe autrement ne remplace pas : il se
# fait refuser sur le telephone, apres le telechargement, et le bouton de mise
# a jour devient un bouton qui echoue. Rien dans la construction ne previent de
# cela -- l'APK est valide, il s'installe parfaitement sur un telephone neuf.
#
# Cette valeur n'est pas un secret : elle se lit dans n'importe quel APK
# publie. C'est un temoin. Le jour ou le magasin de cles serait perdu puis
# recree, elle arrete la livraison ici plutot que de la laisser partir vers des
# telephones qui la refuseront un par un.
empreinte_attendue=56aa274b98215cedfd12b5c6505b776d5df1817172d1f441f0a9bfca7009c5d4

lire()   { grep -E "^$1=" "$proprietes" | head -1 | cut -d= -f2 | tr -d '[:space:]'; }
ecrire() {
    grep -qE "^$1=" "$proprietes" || { echo "clé $1 absente de $proprietes" >&2; exit 1; }
    sed -i -E "s|^$1=.*|$1=$2|" "$proprietes"
}
publie() { jq -r --arg p "$1" '.[$p].versionCode // 0' "$manifeste"; }

paquet_de() { case $1 in guilde) echo net.ryzom.zyroom ;; dev) echo net.ryzom.zyroom.dev ;; esac; }

# Les trois choses qu'Android compare pour decider d'accepter une mise a jour,
# relues dans l'APK lui-meme et non dans les variables qui ont servi a le
# construire : la cle qui l'a signe, l'identifiant du paquet, le numero de
# version. Une seule qui derive, et l'APK cesse d'etre une mise a jour de celui
# des joueurs pour devenir une application etrangere.
verifie_apk() {
    local apk=$1 paquet=$2 code=$3 empreinte badging

    empreinte=$("$apksigner" verify --print-certs "$apk" 2>/dev/null \
        | sed -n 's/^Signer #1 certificate SHA-256 digest: //p')
    [ "$empreinte" = "$empreinte_attendue" ] || {
        echo "Erreur : l'APK construit n'est pas signe par la cle de V-RyLune." >&2
        echo "  attendu : $empreinte_attendue" >&2
        echo "  trouve  : ${empreinte:-aucune signature lisible}" >&2
        echo "Livre ainsi, il ne s'installerait sur aucun telephone qui a deja" >&2
        echo "l'application : Android refuse une signature differente." >&2
        exit 1
    }

    # "package: name='net.ryzom.zyroom' versionCode='45' versionName='2.39' ..."
    # Les valeurs sont entre apostrophes, dans cet ordre : le 2e champ est le
    # nom du paquet, le 4e son versionCode.
    badging=$("$aapt2" dump badging "$apk" | head -1)
    [ "$(cut -d"'" -f2 <<<"$badging")" = "$paquet" ] || {
        echo "Erreur : l'APK annonce le paquet $(cut -d"'" -f2 <<<"$badging")," >&2
        echo "la ou $paquet etait attendu. Un identifiant different fait une" >&2
        echo "seconde application a cote de l'ancienne, pas une mise a jour." >&2
        exit 1
    }
    [ "$(cut -d"'" -f4 <<<"$badging")" = "$code" ] || {
        echo "Erreur : l'APK porte le versionCode $(cut -d"'" -f4 <<<"$badging")," >&2
        echo "la ou $code va etre annonce dans version.json. Les telephones" >&2
        echo "verraient une mise a jour qui, une fois installee, se croit deja" >&2
        echo "a jour -- et le bandeau reviendrait a chaque lancement." >&2
        exit 1
    }
}

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

# F-Droid lit fastlane/ dans le code qu'il construit, pas dans le dernier
# commit : une note de version ecrite apres l'etiquette n'est lue par personne.
# D'ou l'avertissement ici, avant la construction, tant qu'il reste le temps de
# l'ecrire. Seule la variante des joueurs a une fiche F-Droid.
if [[ " ${variantes[*]} " == *" guilde "* ]]; then
    notes=$racine/../fastlane/metadata/android
    manquantes=()
    for langue in fr-FR en-US; do
        [ -f "$notes/$langue/changelogs/${codes[guilde]}.txt" ] \
            || manquantes+=("$langue/changelogs/${codes[guilde]}.txt")
    done
    if [ ${#manquantes[@]} -gt 0 ]; then
        echo >&2
        echo "Note de version absente pour le versionCode ${codes[guilde]} :" >&2
        printf '  fastlane/metadata/android/%s\n' "${manquantes[@]}" >&2
        echo "Elle doit exister avant l'étiquette : F-Droid lit fastlane/ dans le" >&2
        echo "code qu'il construit, et ne verra jamais une note écrite après." >&2
        echo >&2
    fi
fi

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
    verifie_apk "$construit" "$paquet" "${codes[$v]}"

    # Pas de parenthèses dans les noms de fichiers : ils finissent dans une URL
    # et dans une ligne de commande, où elles se font réécrire ou avaler. La
    # règle vient des pièces jointes des Releases, que GitHub renommait en
    # points — on ne publie plus ainsi, mais elle reste bonne.
    # Les deux variantes sont servies depuis la page, sous un nom fixe que
    # version.json annonce une fois pour toutes. Une Release GitHub ferait
    # aussi bien pour le joueur, mais elle demande un jeton d'API : la
    # publication cesserait d'être faisable d'un seul geste, et il faudrait
    # que la Release existe *avant* que version.json l'annonce, sinon les
    # téléphones verraient un numéro neuf et un téléchargement mort.
    # La copie datée dans dist/ n'est donc pas ce qu'on joindrait à une
    # Release : c'est l'archive locale de ce qui est parti, la seule façon de
    # retrouver l'APK d'un numéro donné une fois la page écrasée par le suivant.
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
    "$apksigner" verify --print-certs "$racine/dist/$fichier" \
        | grep -E 'Signer #1 certificate DN'
done

# L'etiquette ne peut pas etre posee ici : le commit qui fige le nouveau numero
# n'existe pas encore -- c'est l'etape 2 ci-dessous. Le script prepare donc la
# commande exacte, numeros deja remplis. Sans elle, F-Droid ne retrouve pas le
# code d'une version : sa recette va chercher l'etiquette « v<numero> ».
etiquettes=""
for v in "${variantes[@]}"; do
    case $v in
        guilde) tag="v${noms[$v]}";      titre="V-RyLune ${noms[$v]} (versionCode ${codes[$v]})" ;;
        dev)    tag="v${noms[$v]}-dev";  titre="V-RyLune (dev) ${noms[$v]} (versionCode ${codes[$v]})" ;;
    esac
    etiquettes+="       git tag -a $tag -m \"$titre\"
"
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

FIN

cat <<FIN
  2. valider le nouveau numéro, puis étiqueter le commit :

       git add -u && git commit
$etiquettes       git push origin main --follow-tags

     L'étiquette dit quel code a produit quel APK : sans elle, retrouver la
     version qu'un joueur a sur son téléphone devient une fouille, et la
     recette F-Droid, qui va chercher « v<numéro> », ne construit rien.

FIN

cat <<'FIN'
  3. vérifier depuis le site, et non depuis dist/ : que l'URL annoncée par
     version.json répond, que son empreinte est celle de l'APK construit, et
     que le versionCode relu par « aapt2 dump badging » est le neuf.

     Pas de Release GitHub : les deux APK sont servis par la page, sous un nom
     fixe que version.json annonce. Une Release demanderait un jeton d'API et
     devrait exister avant d'être annoncée.
FIN
