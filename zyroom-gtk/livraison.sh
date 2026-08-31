#!/usr/bin/env bash
#
# Livraison d'une variante GTK, d'un seul geste.
#
#   ./livraison.sh dev          → variante du mainteneur, numéro inchangé
#   ./livraison.sh guilde 0.4   → variante des joueurs, renumérotée 0.4
#   ./livraison.sh tout 0.4     → les deux sous le même numéro
#   ./livraison.sh tout guilde=0.25 dev=0.42  → les deux, chacun le sien
#   ./livraison.sh dev 0.4 --sans-signature  → renumérote et construit, s'arrête
#                                             avant tout ce qui demande la clé
#
# **Renuméroter les deux : un seul appel, la forme `variante=numéro`.** Les deux
# variantes n'ont pas le même compteur, et `window.py` porte les **deux** noms —
# c'est lui qui choisit selon `FLATPAK_ID`, pour que l'application se nomme aussi
# quand on la lance depuis les sources. Livrer l'une puis l'autre en deux appels
# fige donc dans la première le numéro que la seconde avait *avant* : la branche
# est morte dans son bac à sable, mais le fichier ment. En un appel, les deux
# numéros sont posés avant la moindre construction.
#
# Ce que le script fait, dans l'ordre : recopier le numéro là où il s'affiche,
# construire, verser le résultat dans le dépôt publié, le signer, refaire son
# sommaire, puis fabriquer le bundle autonome. Rien n'est envoyé sur GitHub : il
# s'arrête au bord et affiche ce qui reste à pousser.
#
# **La signature se fait ici, sur l'hôte, et non pendant la construction.** Le
# bac à sable de flatpak-builder a son propre agent GPG, sans accès à l'écran ni
# à la phrase de passe en cache : demander --gpg-sign à la construction échoue
# sans expliquer pourquoi. On construit donc sans signer, et on signe après.
#
# Il faudra taper la phrase de passe de la clé. Elle est dans le KeePassXC de
# Ludo ; sans elle, rien ne se publie — et la perdre obligerait chaque joueur à
# désinstaller puis réinstaller.
#
# `--sans-signature` sépare les deux moitiés du travail : renuméroter et
# construire ne demande rien, signer si. Cela permet de préparer une livraison —
# et de découvrir une construction cassée — avant d'aller chercher la phrase de
# passe, au lieu de l'apprendre juste après l'avoir tapée. Relancer ensuite la
# même commande sans le drapeau reprend là où l'on s'était arrêté.
set -euo pipefail

racine=$(cd "$(dirname "$0")" && pwd)
cd "$racine"

depot_publie=$racine/../pages/repo
url_depot=https://xiom-dev.github.io/zyroom-gtk-android/repo/
cle_fichier=$racine/../.signing-key-id
cle_publique=$HOME/cle-signature-zyroom/cle-publique-zyroom.asc
proprietes=$racine/version.properties
builder="flatpak run org.flatpak.Builder"

usage() { sed -n '3,10p' "$0" | sed 's/^# \?//'; exit 2; }

sans_signature=0
arguments=()
for argument in "$@"; do
    case $argument in
        --sans-signature) sans_signature=1 ;;
        *)                arguments+=("$argument") ;;
    esac
done
set -- ${arguments[@]+"${arguments[@]}"}

case ${1:-} in
    guilde|dev) variantes=("$1") ;;
    tout)       variantes=(guilde dev) ;;
    *)          usage ;;
esac
selection=$1
shift

# Les numéros demandés, une entrée par variante. Deux écritures : un numéro nu,
# qui vaut pour toutes les variantes livrées, ou des couples `variante=numéro`.
# Sans rien, chaque variante garde le sien.
declare -A numero=()
for argument in "$@"; do
    case $argument in
        guilde=*|dev=*)
            cible=${argument%%=*}
            # Renuméroter une variante qu'on ne construit pas laisserait
            # `version.properties` en avance sur ce qui est publié.
            [[ " ${variantes[*]} " == *" $cible "* ]] || {
                echo "Erreur : $argument renumérote « $cible », qui n'est pas livrée ici." >&2
                echo "Utilise « tout » pour livrer les deux." >&2
                exit 1
            }
            numero[$cible]=${argument#*=}
            ;;
        *)  for v in "${variantes[@]}"; do numero[$v]=$argument; done ;;
    esac
done
# Ce qu'il faudra retaper après --sans-signature, à l'identique.
rappel_arguments=$*

# Garde-fous : mieux vaut refuser tôt que livrer à moitié.
[ -d "$depot_publie" ] || {
    echo "Erreur : $depot_publie introuvable — le dépôt publié n'est pas dans" >&2
    echo "cet arbre. Récupère la branche gh-pages dans ../pages/ avant de livrer." >&2
    exit 1
}
[ -f "$cle_fichier" ] || { echo "Erreur : $cle_fichier absent (identifiant de la clé)." >&2; exit 1; }
cle=$(tr -d '[:space:]' < "$cle_fichier")
gpg --list-secret-keys "$cle" >/dev/null 2>&1 || {
    echo "Erreur : la clé privée $cle est introuvable dans ton trousseau." >&2
    echo "Elle est sauvegardée dans ~/cle-signature-zyroom/ et dans KeePassXC." >&2
    exit 1
}
[ -f "$cle_publique" ] || {
    echo "Erreur : clé publique absente de $cle_publique — le bundle ne pourrait" >&2
    echo "pas embarquer de quoi vérifier ses propres mises à jour." >&2
    exit 1
}
flatpak info org.flatpak.Builder >/dev/null 2>&1 || {
    echo "Erreur : org.flatpak.Builder n'est pas installé." >&2
    echo "  flatpak install --user flathub org.flatpak.Builder" >&2
    exit 1
}

lire()   { grep -E "^$1=" "$proprietes" | head -1 | cut -d= -f2 | tr -d '[:space:]'; }
ecrire() {
    grep -qE "^$1=" "$proprietes" || { echo "clé $1 absente de $proprietes" >&2; exit 1; }
    sed -i -E "s|^$1=.*|$1=$2|" "$proprietes"
}

app_de()      { case $1 in guilde) echo net.ryzom.zyroomgtk ;; dev) echo net.ryzom.zyroomgtk.dev ;; esac; }
manifeste_de(){ echo "packaging/$(app_de "$1").yml"; }
# Le nom affiché — menu, logithèque, alternateur de tâches. **Sans numéro** : il
# nommait la version autant que l'application, si bien que le menu changeait de
# ligne à chaque livraison. Le numéro se lit maintenant là où on le cherche : la
# logithèque le tient de <release>, l'À propos de VERSION.
etiquette_de(){ case $1 in guilde) echo "ZyRoom-GTK" ;; dev) echo "ZyRoom-GTK(dev)" ;; esac; }
# Le nom de fichier, lui, garde le numéro — sans quoi chaque livraison
# écraserait la précédente dans dist/ — et n'aura jamais de parenthèses : ces
# noms-là finissent dans une URL et dans une ligne de commande, où elles se font
# réécrire ou avaler. La règle vient des pièces jointes des Releases, que GitHub
# renommait en points ; on ne publie plus ainsi, mais elle reste bonne.
fichier_de()  { case $1 in guilde) echo "ZyRoom-GTK-$2" ;; dev) echo "ZyRoom-GTK-dev-$2" ;; esac; }

for v in "${variantes[@]}"; do
    nom=${numero[$v]:-$(lire "$v.versionName")}
    ecrire "$v.versionName" "$nom"
    app=$(app_de "$v")
    etiquette=$(etiquette_de "$v")
    printf '%-7s %s → %s %s\n' "$v" "$app" "$etiquette" "$nom"

    # 1. Le nom, là où il s'affiche : menu, logithèque, barre des tâches. Il ne
    # bouge plus d'une livraison à l'autre, mais il est réécrit quand même — un
    # fichier qu'on ne récrit jamais est un fichier qui dérive en silence.
    sed -i -E "s|^Name=.*|Name=$etiquette|" "data/$app.desktop"
    sed -i -E "0,/<name>.*<\/name>/s||<name>$etiquette</name>|" "data/$app.metainfo.xml"

    # Et dans <releases>, qui est le seul numéro qu'AppStream comprenne comme
    # une version : `flatpak list`, `flatpak remote-info` et GNOME Logiciels
    # lisent celui-là, pas le <name>. Il portait « 6.0.0 » du 1er août — hérité
    # du zyRoom 6 de Misugi et jamais touché — pendant que l'application
    # s'appelait 0.29 : la logithèque annonçait donc une version que rien
    # d'autre ne connaissait. Une seule entrée, celle qu'on publie : tenir un
    # historique demanderait un texte par version, et personne ne le lira dans
    # une application qui se met à jour toute seule.
    grep -q '<release version=' "data/$app.metainfo.xml" || {
        echo "Erreur : pas de ligne <release> dans data/$app.metainfo.xml." >&2
        echo "Sans elle, la logithèque garderait l'ancien numéro sans rien dire." >&2
        exit 1
    }
    sed -i -E "s|<release version=\"[^\"]*\" date=\"[^\"]*\"/>|<release version=\"$nom\" date=\"$(date +%F)\"/>|" \
        "data/$app.metainfo.xml"
    # Relu par le validateur quand il est là : un `sed` sur du XML se trompe en
    # silence, et le manifeste ne serait refusé qu'à la construction suivante.
    if command -v appstreamcli >/dev/null; then
        appstreamcli validate --no-net "data/$app.metainfo.xml" >/dev/null || {
            echo "Erreur : data/$app.metainfo.xml ne valide plus après renumérotation." >&2
            exit 1
        }
    fi
done

# VERSION choisit selon FLATPAK_ID : les deux numéros sont dans le même fichier,
# et doivent suivre les deux variantes même si une seule est livrée. APP_NAME,
# lui, ne dépend plus du numéro et n'est plus touché ici.
python3 - "$(lire guilde.versionName)" "$(lire dev.versionName)" <<'PY'
import re, sys
guilde, dev = sys.argv[1], sys.argv[2]
chemin = "zyroom/window.py"
source = open(chemin, encoding="utf-8").read()
source, remplaces = re.subn(r'^VERSION = ".*" if _DEV else ".*"$',
                            f'VERSION = "{dev}" if _DEV else "{guilde}"',
                            source, count=1, flags=re.M)
if remplaces != 1:
    sys.exit("Erreur : la ligne VERSION de zyroom/window.py n'a pas été reconnue.")
open(chemin, "w", encoding="utf-8").write(source)
PY

for v in "${variantes[@]}"; do
    app=$(app_de "$v")
    nom=$(lire "$v.versionName")
    fichier=$(fichier_de "$v" "$nom")
    suffixe=$([ "$v" = dev ] && echo "-dev" || echo "")

    echo
    echo "── construction de $app"
    $builder --user --force-clean --disable-updates \
        --repo="build-repo$suffixe" "build-dir$suffixe" "$(manifeste_de "$v")" >/dev/null

    if [ "$sans_signature" = 1 ]; then
        echo "── construit dans build-repo$suffixe, non signé"
        continue
    fi

    echo "── versement dans le dépôt publié, et signature"
    # La signature demande la phrase de passe : c'est ici qu'elle est réclamée,
    # sur l'hôte, où l'agent GPG sait ouvrir sa fenêtre.
    flatpak build-commit-from --src-repo="build-repo$suffixe" \
        --gpg-sign="$cle" "$depot_publie" "app/$app/x86_64/master"

    mkdir -p dist
    echo "── bundle autonome"
    # --repo-url et --gpg-keys : le fichier installé configure lui-même sa
    # source de mises à jour et la clé qui la signe. Sans eux, le joueur devrait
    # ajouter le dépôt à la main — trois commandes de terminal que personne ne
    # tapera.
    flatpak build-bundle "$depot_publie" "dist/$fichier.flatpak" \
        --repo-url="$url_depot" --gpg-keys="$cle_publique" "$app" master
    (cd dist && sha256sum "$fichier.flatpak")

    # Une copie sous un nom fixe sur la page : c'est le lien qu'on donne aux
    # joueurs. Il ne change jamais et pointe droit sur le fichier — une adresse
    # qui change à chaque version, ou qui mène à une page où il faut chercher,
    # ne convient pas à des gens qui ne connaissent pas GitHub.
    servi=$([ "$v" = dev ] && echo "ZyRoom-GTK-dev.flatpak" || echo "ZyRoom-GTK.flatpak")
    cp "dist/$fichier.flatpak" "$racine/../pages/$servi"
done

if [ "$sans_signature" = 1 ]; then
    cat <<FIN

Préparé, rien n'est signé ni publié. Les numéros sont posés et la
construction passe. Pour terminer, la phrase de passe à la main :

    ./livraison.sh $selection $rappel_arguments

FIN
    exit 0
fi

echo
echo "── sommaire du dépôt"
flatpak build-update-repo --generate-static-deltas --prune \
    --gpg-sign="$cle" "$depot_publie"

# L'etiquette ne peut pas etre posee ici : le commit qui fige le nouveau numero
# n'existe pas encore -- c'est l'etape 2 ci-dessous. Le script prepare donc la
# commande exacte, numeros deja remplis. Les numeros sont relus dans
# version.properties, que la boucle de construction vient d'y ecrire : la
# variable de boucle, elle, ne vaut plus que pour la derniere variante.
etiquettes=""
for v in "${variantes[@]}"; do
    livre=$(lire "$v.versionName")
    case $v in
        guilde) tag="gtk-$livre";      titre="ZyRoom-GTK $livre" ;;
        dev)    tag="gtk-dev-$livre";  titre="ZyRoom-GTK (dev) $livre" ;;
    esac
    etiquettes+="       git tag -a $tag -m \"$titre\"
"
done

cat <<'FIN'

Reste à faire, à la main — rien n'a été envoyé :

  1. publier le dépôt et la page :

       cd ..
       tampon=$(mktemp -u)
       (cd pages && GIT_INDEX_FILE=$tampon git --git-dir=../.git --work-tree=. add -Af .)
       arbre=$(GIT_INDEX_FILE=$tampon git write-tree)
       commit=$(git commit-tree "$arbre" -m "Site : dépôt Flatpak")
       git push -f origin "$commit:refs/heads/gh-pages"

FIN

cat <<FIN
  2. valider les numéros et les noms, puis étiqueter le commit :

       git add -u && git commit
$etiquettes       git push origin main --follow-tags

     Flatpak met à jour sur l'empreinte du commit, pas sur ce numéro : ici
     l'étiquette ne sert pas à la mise à jour, elle sert à retrouver le code
     qui a produit un bundle donné.

FIN

cat <<'FIN'
  3. vérifier depuis une installation propre :
       flatpak update net.ryzom.zyroomgtk.dev
FIN
