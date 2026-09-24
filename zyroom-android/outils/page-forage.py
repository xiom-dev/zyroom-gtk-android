#!/usr/bin/env python3
"""Fabrique la page de relevé du forage pour xiom.be/forage.

Le classeur de la guilde porte un onglet vierge en **six** bandes d'humidité —
Worst, Bad2, Bad1, Good1, Good2, Best. Les relevés déjà faits montrent que Bad1
vaut toujours Bad2 et Good1 toujours Good2 : huit cent trente-six paires, sans
une exception. Les deux moitiés sont donc réunies ici, ce qui ramène le tableau
à **quatre colonnes par saison**, celles que le jeu rend lui-même — et divise
par deux le nombre de cases à cocher sur le terrain.

La page se coche d'un clic : vide → `x` (ça sort) → `−` (ça ne sort pas) →
vide, et **tout le monde voit les croix de tout le monde** — le relevé vit sur
le serveur, dans un fichier JSON que `releve.php` tient à jour.

**Lecture libre, écriture sur adresse secrète.** Sans clef dans l'adresse, la
page se lit et ne se coche pas. Avec `?k=…`, elle devient inscriptible. La clef
est gardée dans `~/.config/zyroom/forage.cle`, hors du dépôt, et recopiée dans
`releve.php` — que le serveur exécute, et ne montre donc jamais. Si elle fuite,
on en tire une autre et l'ancienne ne vaut plus rien.

Chaque croix porte le nom de la foreuse : sur un tableau rempli à plusieurs sur
des mois, savoir à qui demander vaut cher le jour où deux relevés se
contredisent.

    python3 outils/page-forage.py

Trois fichiers sont écrits dans `site-domaine/forage/`, à monter tels quels :
`index.html`, `releve.php` et `.htaccess`. Le fichier de données et ses
sauvegardes, PHP les crée tout seul.

**Rien de tout cela n'est écrit sur la page.** Les foreuses ne suivent pas le
développement : pourquoi les colonnes ont été réunies, où sont gardées les
croix, comment on fusionne deux relevés — ce sont des explications d'auteur, et
trop d'information tue l'information. La page dit comment cocher, et s'arrête.
"""
import base64
import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from table_forage import CLASSEUR, feuilles                      # noqa: E402

_ANDROID = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEPOT = os.path.dirname(_ANDROID)

#: Les symboles du jeu, ceux que ZyRoom affiche deja dans son ecran Meteo.
#: Une coquille pour la carapace, une goutte pour la seve : l'oeil les
#: reconnait plus vite qu'il ne lit « Carapace ».
SYMBOLES = os.path.join(_DEPOT, "zyroom-gtk", "zyroom", "symboles")
CIBLE = os.path.join(_DEPOT, "site-domaine", "forage", "index.html")

#: La clef d'ecriture. Hors du depot, comme le jeton du tracker : elle finit
#: recopiee dans `releve.php`, que le serveur execute et ne montre jamais.
CLE_FICHIER = os.path.expanduser("~/.config/zyroom/forage.cle")

#: Le mot de passe de lecture, et le sel du jeton de session.
#:
#: **Pourquoi un mot de passe.** Le relevé dit où et quand sortent les
#: suprêmes des Primes : c'est le travail de plusieurs mois de foreuses, et
#: les guildes concurrentes forent les mêmes spots. La grille vide reste
#: publique — elle n'apprend rien — mais les croix passent derrière un mot
#: de passe partagé.
#:
#: Les deux fichiers restent hors du dépôt, comme la clef d'écriture.
MOT_DE_PASSE_FICHIER = os.path.expanduser("~/.config/zyroom/forage.motdepasse")
SEL_FICHIER = os.path.expanduser("~/.config/zyroom/forage.sel")

ONGLET = "Original vierge"
SAISONS = ("Printemps", "Été", "Automne", "Hiver")

#: Les quatre zones des Primes. Le classeur leur donne un onglet chacune, et
#: elles ne sortent pas les memes matieres au meme moment -- c'est meme tout
#: l'interet du releve. Une page sans elles ne voulait rien dire.
ZONES = ("Sources Interdites", "Terre de la Continuité",
         "Cité Engloutie", "Profondeurs Interdites")

#: Les quatre conditions du jeu, avec la fourchette d'humidite que le tracker
#: affiche. Le nom anglais est garde : c'est celui du classeur et du tracker,
#: donc celui que les foreuses ont sous les yeux.
#: **« Médiocre » et non « Exécrable ».** C'est le mot du tracker d'atys.us et
#: du graphe de Ballistic Mystix, ceux que les foreuses ont sous les yeux à
#: côté de cette page. Deux noms pour la même bande d'humidité forçaient à
#: traduire de tête à chaque coup d'œil.
#:
#: Les bornes sont celles du jeu, sans arrondi : 16,6 / 16,7 et 83,3 / 83,4
#: sont des frontières, pas des approximations.
CONDITIONS = (("Médiocre", "Worst", "83,4 – 100 %"),
              ("Mauvaise", "Bad", "50 – 83,3 %"),
              ("Bonne", "Good", "16,7 – 49,9 %"),
              ("Excellente", "Best", "0 – 16,6 %"))

QUALITES = ("Supp", "XL", "Choix")


def clef() -> str:
    """La clef d'écriture, lue une fois pour toutes."""
    if not os.path.isfile(CLE_FICHIER):
        raise SystemExit(
            f"Clef absente : {CLE_FICHIER}\n"
            "En tirer une : python3 -c \"import secrets; "
            "print('forage-' + secrets.token_hex(6))\" > " + CLE_FICHIER)
    with open(CLE_FICHIER, encoding="utf-8") as fh:
        return fh.read().strip()


def empreinte_mot_de_passe() -> str:
    """L'empreinte bcrypt du mot de passe de lecture.

    Le mot de passe en clair ne quitte jamais la machine : c'est son empreinte
    qui part sur le serveur, et `password_verify` fait le reste. Douze tours,
    de quoi rendre une attaque hors ligne coûteuse si le fichier PHP fuyait.
    """
    if not os.path.isfile(MOT_DE_PASSE_FICHIER):
        raise SystemExit(
            f"Mot de passe absent : {MOT_DE_PASSE_FICHIER}\n"
            "En poser un : echo 'ma-phrase' > " + MOT_DE_PASSE_FICHIER)
    import bcrypt
    with open(MOT_DE_PASSE_FICHIER, encoding="utf-8") as fh:
        phrase = fh.read().strip()
    # PHP attend le prefixe « $2y$ » ; c'est le meme algorithme que « $2b$ ».
    return "$2y$" + bcrypt.hashpw(phrase.encode(),
                                  bcrypt.gensalt(12)).decode()[4:]


def sel() -> str:
    """Le secret qui signe le jeton de session.

    Pas de session PHP : le serveur ne garde rien. Le cookie porte sa propre
    date d'expiration et une signature HMAC — le serveur la revérifie, et
    n'a donc aucun fichier de session à écrire ni à nettoyer.
    """
    if not os.path.isfile(SEL_FICHIER):
        raise SystemExit(
            f"Sel absent : {SEL_FICHIER}\n"
            "En tirer un : python3 -c \"import secrets; "
            "print(secrets.token_hex(24))\" > " + SEL_FICHIER)
    with open(SEL_FICHIER, encoding="utf-8") as fh:
        return fh.read().strip()


def symbole(famille: str) -> str:
    """L'image d'une famille, en data-URI — la page reste un seul fichier.

    Onze fichiers à monter par FTP au lieu d'un, pour trente kilooctets
    d'images, c'était dix occasions d'en oublier un.
    """
    anglais = famille.split("/")[-1].strip().lower()
    # « Node », chez Ryzom, c'est la boucle de bois : son image porte les deux.
    fichier = "mp_wood_node.png" if anglais == "node" else f"mp_{anglais}.png"
    chemin = os.path.join(SYMBOLES, fichier)
    if not os.path.isfile(chemin):
        raise SystemExit(f"symbole introuvable : {chemin}")
    with open(chemin, "rb") as fh:
        return "data:image/png;base64," + base64.b64encode(fh.read()).decode()


def catalogue() -> list:
    """[(famille, [matières])] — dans l'ordre exact de l'onglet vierge."""
    familles: list = []
    for ligne in feuilles(CLASSEUR)[ONGLET]:
        ligne = (list(ligne) + [""] * 26)[:26]
        nom, qualite = ligne[0].strip(), ligne[1].strip()
        if nom and "/" in nom and not qualite:
            familles.append((nom, []))
        elif qualite == "Choix" and nom and familles:
            familles[-1][1].append(nom)
    return familles


def grille(familles: list) -> str:
    """Le tableau d'une saison : familles, matières, trois qualités."""
    lignes = []
    for rang_famille, (famille, matieres) in enumerate(familles):
        # Les quatre conditions redites sur la ligne jaune de chaque famille.
        # Le tableau fait cent quarante et une lignes : meme avec l'en-tete
        # colle en haut, on perd la colonne ou l'on vise en descendant.
        # La premiere famille n'en a pas besoin : le vrai en-tete est juste
        # au-dessus d'elle, et le redire ferait deux lignes identiques collees.
        # L'embleme devant le nom, a cinq pixels, l'ensemble centre dans sa
        # cellule. Il l'a d'abord precede sans que la cellule soit centree :
        # le nom se trouvait alors pousse d'une largeur d'icone vers la droite.
        # Le nom dans sa propre balise : c'est lui, et lui seul, que le
        # centrage doit prendre en compte.
        titre = (f'<img class="embleme" src="{symbole(famille)}" alt="">'
                 f'<span class="nom-famille">{html.escape(famille)}</span>')
        if rang_famille == 0:
            # Meme largeur de cellule que les autres familles, pour que les dix
            # noms se centrent sur la meme colonne. Les quatre cases de droite
            # restent vides : le vrai en-tete est juste au-dessus, et redire
            # les conditions ferait deux lignes identiques collees.
            lignes.append(f'<tr class="famille"><th colspan="2">{titre}</th>'
                          + '<td class="vide"></td>' * len(CONDITIONS)
                          + '</tr>')
        else:
            lignes.append(
                f'<tr class="famille"><th colspan="2">{titre}</th>'
                # La plage aussi, et pas seulement le nom : le tableau est
                # long, et c'est ce rappel-ci qu'on a sous les yeux en le
                # parcourant, pas l'en-tete reste tout en haut.
                + "".join(f'<th class="rappel">{fr}'
                          f'<span class="plage">{plage}</span></th>'
                          for fr, _c, plage in CONDITIONS)
                + "</tr>")
        for matiere in matieres:
            # Le « ² » du classeur marquait les matieres a stocker en priorite
            # pour le GH. On le retire : ces listes datent de 2009 et une partie
            # n'est plus vraie, et de toute facon cela n'aide pas a remplir le
            # tableau -- qui est le seul but de cette page.
            propre = matiere.replace("²", "").strip()
            for rang, qualite in enumerate(QUALITES):
                cles = "".join(
                    f'<td class="case" data-cle="{html.escape(propre)}|{qualite}'
                    f'|{court}"></td>'
                    for _fr, court, _plage in CONDITIONS)
                if rang == 0:
                    debut = (f'<th class="matiere" rowspan="3">'
                             f'{html.escape(propre)}</th>')
                else:
                    debut = ""
                lignes.append(f'<tr class="q-{qualite.lower()}">{debut}'
                              f'<th class="qualite">{qualite}</th>{cles}</tr>')
    return "\n".join(lignes)



PHP = """<?php
// Le releve commun du forage des Primes, tenu dans un simple fichier JSON.
//
// GET  : rend l'etat entier. Lecture libre.
// POST : une case a la fois, et seulement avec la bonne clef.
//
// Trois valeurs : « x » vu sur place, « - » vu absent, « ? » donne par une
// autre source et pas encore confirme en jeu.
//
// Pourquoi un fichier et pas une base : le releve tient en quelques dizaines
// de kilooctets, il s'ouvre dans un editeur de texte le jour ou quelque chose
// cloche, et il se sauvegarde en le recopiant. Une base pour cela couterait
// plus d'ennuis qu'elle n'en eviterait.
declare(strict_types=1);

const CLE = '__CLE__';
// L'empreinte du mot de passe de lecture, et le secret qui signe le jeton.
// Le mot de passe en clair n'est jamais monte ici.
const EMPREINTE = '__EMPREINTE__';
const SEL = '__SEL__';
const COOKIE = 'forage';
// Trente jours : assez pour ne pas le retaper a chaque session, assez court
// pour qu'un depart de la guilde finisse par fermer la porte.
const DUREE = 30 * 24 * 3600;
const FICHIER = __DIR__ . '/releve.json';
const SAUVEGARDES = __DIR__ . '/sauvegardes';
const MAX_SAUVEGARDES = 60;
const MAX_CORPS = 4096;

// Ce qu'une case a le droit d'etre. On valide contre ces listes plutot que
// contre une expression : une cle inventee n'entrera pas dans le fichier, et
// le relever se lit encore dans six mois.
const ZONES = __ZONES__;
const SAISONS = __SAISONS__;
const QUALITES = __QUALITES__;
const CONDITIONS = __CONDITIONS__;
const MATIERES = __MATIERES__;

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

// ------------------------------------------------------------- le garde
//
// **Pourquoi.** Le releve dit ou et quand sortent les supremes des Primes :
// des mois de forage, et les guildes concurrentes visent les memes spots.
// La grille vide reste publique -- elle n'apprend rien, elle ne contient pas
// une seule croix -- mais les donnees passent derriere un mot de passe.
//
// Deux facons d'entrer : la clef d'ecriture, qui ouvre tout comme avant, ou
// le mot de passe de lecture, qui ne donne que la lecture.
//
// **Pas de session PHP.** Le serveur ne garde rien : le cookie porte sa date
// d'expiration et une signature HMAC, que le serveur revalide. Rien a ecrire,
// rien a nettoyer, et deux hebergements se comportent pareil.

function jeton(int $expire): string
{
    return $expire . '.' . hash_hmac('sha256', (string) $expire, SEL);
}

function jeton_valide(string $recu): bool
{
    $morceaux = explode('.', $recu, 2);
    if (count($morceaux) !== 2 || !ctype_digit($morceaux[0])) {
        return false;
    }
    $expire = (int) $morceaux[0];
    if ($expire < time()) {
        return false;
    }
    // hash_equals : la comparaison ne doit pas fuir la signature par le temps
    // qu'elle met a echouer.
    return hash_equals(jeton($expire), $recu);
}

function connecte(): bool
{
    // Trois endroits ou le jeton peut se trouver, dans cet ordre.
    //
    // **Pourquoi pas le cookie seul.** Un navigateur regle pour effacer les
    // cookies a la fermeture, ou en navigation privee permanente, pose le
    // cookie puis ne le renvoie jamais : la connexion reussit, la lecture
    // suivante echoue, et le formulaire revient sans un mot d'explication.
    // La page garde donc aussi le jeton de son cote et le presente dans un
    // en-tete -- ce qui ne depend d'aucun reglage de cookies.
    //
    // L'en-tete plutot que l'adresse : un jeton dans une URL finit dans les
    // journaux du serveur et dans l'historique du navigateur.
    foreach ([
        $_SERVER['HTTP_X_FORAGE'] ?? '',
        $_COOKIE[COOKIE] ?? '',
    ] as $candidat) {
        if ($candidat !== '' && jeton_valide((string) $candidat)) {
            return true;
        }
    }
    return false;
}

function porte_la_clef(array $demande = []): bool
{
    $fournie = (string) ($demande['cle'] ?? ($_GET['k'] ?? ''));
    return $fournie !== '' && hash_equals(CLE, $fournie);
}

function etat(): array
{
    if (!is_file(FICHIER)) {
        return ['cases' => (object) [], 'maj' => null];
    }
    $lu = json_decode((string) file_get_contents(FICHIER), true);
    if (!is_array($lu) || !isset($lu['cases']) || !is_array($lu['cases'])) {
        return ['cases' => (object) [], 'maj' => null];
    }
    return ['cases' => (object) $lu['cases'], 'maj' => $lu['maj'] ?? null];
}

function repond(int $code, array $corps): never
{
    http_response_code($code);
    echo json_encode($corps, JSON_UNESCAPED_UNICODE);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    // **La clef n'ouvre plus la porte, elle ne donne que le droit d'ecrire.**
    // Le but de cette page est d'encoder le tableau, pas de l'admirer : les
    // deux adresses -- avec clef ou sans -- demandent donc le mot de passe.
    if (!connecte()) {
        repond(401, ['erreur' => 'mot de passe']);
    }
    repond(200, etat());
}

$brut = (string) file_get_contents('php://input', false, null, 0, MAX_CORPS);
$demande = json_decode($brut, true);
if (!is_array($demande)) {
    repond(400, ['erreur' => 'requete illisible']);
}

// L'ouverture de porte : un mot de passe contre un cookie signe. Le cookie
// est httponly (le JavaScript de la page ne le lit jamais), samesite strict
// (il ne part pas depuis un autre site) et secure (jamais en clair).
if (($demande['action'] ?? '') === 'entrer') {
    $mdp = (string) ($demande['mdp'] ?? '');
    // Une seconde de retard : une attaque par essais successifs devient
    // interminable, et une foreuse qui se trompe ne le remarque pas.
    usleep(1000000);
    if (!password_verify($mdp, EMPREINTE)) {
        repond(403, ['erreur' => 'mot de passe']);
    }
    $expire = time() + DUREE;
    setcookie(COOKIE, jeton($expire), [
        'expires' => $expire,
        'path' => dirname((string) ($_SERVER['SCRIPT_NAME'] ?? '/')),
        'secure' => true,
        'httponly' => true,
        'samesite' => 'Strict',
    ]);
    // Le jeton est rendu en clair : la page le garde de son cote, pour les
    // navigateurs qui ne conservent pas les cookies.
    repond(200, ['ok' => true, 'jeton' => jeton($expire)]);
}
// hash_equals plutot que == : la comparaison ne doit pas fuir la clef par le
// temps qu'elle met a echouer.
if (!hash_equals(CLE, (string) ($demande['cle'] ?? ''))) {
    repond(403, ['erreur' => 'clef']);
}

$case = (string) ($demande['case'] ?? '');
$valeur = (string) ($demande['valeur'] ?? '');
$foreuse = trim((string) ($demande['foreuse'] ?? ''));
// Ni mbstring ni substr : l'un n'est pas garanti sur tous les hebergements,
// l'autre couperait un caractere accentue en deux. PCRE en mode /u fait
// les deux -- ne garder que des lettres, puis s'arreter a vingt-quatre.
$foreuse = (string) preg_replace('/[^\\p{L}\\p{N} \\-\\']/u', '', $foreuse);
$foreuse = (string) preg_replace('/^(.{0,24}).*$/us', '$1', $foreuse);

$morceaux = explode('|', $case);
if (count($morceaux) !== 5
    || !in_array($morceaux[0], ZONES, true)
    || !in_array($morceaux[1], SAISONS, true)
    || !in_array($morceaux[2], MATIERES, true)
    || !in_array($morceaux[3], QUALITES, true)
    || !in_array($morceaux[4], CONDITIONS, true)) {
    repond(400, ['erreur' => 'case inconnue']);
}
if (!in_array($valeur, ['x', '-', '?', ''], true)) {
    repond(400, ['erreur' => 'valeur inconnue']);
}

// Le verrou tient le temps de lire, modifier et reecrire : deux foreuses qui
// cochent dans la meme seconde ne doivent pas s'effacer l'une l'autre.
$fh = fopen(FICHIER, 'c+');
if ($fh === false || !flock($fh, LOCK_EX)) {
    repond(500, ['erreur' => 'fichier verrouille']);
}
$contenu = stream_get_contents($fh);
$lu = json_decode((string) $contenu, true);
$cases = (is_array($lu) && isset($lu['cases']) && is_array($lu['cases']))
    ? $lu['cases'] : [];

// Une sauvegarde avant chaque ecriture : un tableau rempli sur des mois par
// plusieurs foreuses ne doit pas pouvoir disparaitre sur une fausse manoeuvre.
if ($contenu !== '') {
    @mkdir(SAUVEGARDES, 0775, true);
    @file_put_contents(
        SAUVEGARDES . '/releve-' . gmdate('Ymd-His') . '.json', $contenu);
    $vieilles = glob(SAUVEGARDES . '/releve-*.json') ?: [];
    sort($vieilles);
    foreach (array_slice($vieilles, 0, max(0, count($vieilles) - MAX_SAUVEGARDES)) as $v) {
        @unlink($v);
    }
}

if ($valeur === '') {
    unset($cases[$case]);
} else {
    $cases[$case] = ['v' => $valeur, 'qui' => $foreuse,
                     'quand' => gmdate('c')];
}
$sortie = json_encode(['cases' => (object) $cases, 'maj' => gmdate('c')],
                      JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
ftruncate($fh, 0);
rewind($fh);
fwrite($fh, (string) $sortie);
fflush($fh);
flock($fh, LOCK_UN);
fclose($fh);

repond(200, ['ok' => true, 'case' => $case, 'valeur' => $valeur]);
"""

HTACCESS = """# Le releve et ses sauvegardes ne se lisent que par releve.php, jamais en
# direct : le fichier porte le nom des foreuses, et les sauvegardes
# s'enumereraient une a une.
<FilesMatch "\\.json$">
    Require all denied
</FilesMatch>
<IfModule mod_autoindex.c>
    Options -Indexes
</IfModule>

# La page se retouche souvent, et un navigateur qui garde l'ancienne fait
# perdre un aller-retour entier : on croit corriger un defaut deja corrige.
# Elle est legere, et son contenu vient de toute facon du serveur.
<FilesMatch "\\.html$">
    Header set Cache-Control "no-cache, must-revalidate"
</FilesMatch>
"""

GABARIT = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Relevé de forage des Primes</title>
<meta name="description" content="Où et quand sortent les matières des Primes : le relevé de la guilde La Lune Éternelle, à remplir en forant.">
<meta name="theme-color" content="#10171a">
<!-- L'hébergeur ne relaie pas le Cache-Control du .htaccess : vérifié, la
     réponse arrive sans lui. La page se retouche souvent, et un navigateur
     qui garde l'ancienne fait perdre un aller-retour entier. -->
<meta http-equiv="Cache-Control" content="no-cache, must-revalidate">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><circle cx='16' cy='16' r='13' fill='%233f7a68'/><circle cx='20' cy='12' r='11' fill='%2310171a'/></svg>">
<meta property="og:type" content="website">
<meta property="og:title" content="Relevé de forage des Primes">
<meta property="og:url" content="https://xiom.be/forage/">
<style>
  /* Les couleurs de xiom.be, reprises telles quelles. */
  :root {
    color-scheme: dark;
    --fond: #10171a; --surface: #172226; --sarcelle: #3f7a68;
    --clair: #8fbfae; --or: #e8c15a; --texte: #e2e8e6; --faible: #9aa8a5;
    --oui: #4bbf72; --non: #55605e; --dedu: #e8a13a;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 0 16px 48px;
    background: var(--fond); color: var(--texte);
    font-family: system-ui, sans-serif; font-size: 15px;
  }
  header { max-width: 900px; margin: 0 auto; padding: 24px 0 8px; }
  h1 { font-size: 1.4rem; margin: 0 0 8px; color: var(--or); }
  p { margin: 0 0 10px; color: var(--faible); line-height: 1.5; }
  header { max-width: 1180px; margin: 0 auto; padding: 12px 12px 0; }
  a { color: var(--clair); }

  /* **La page defile normalement ; le panneau, lui, ne bouge pas.**
     Deux barres de defilement imbriquees -- une pour la page, une pour la
     zone de droite -- donnaient une page entierement figee, ou l'on ne savait
     plus laquelle on tenait.
     Le panneau s'accroche a douze pixels du haut. Comme il commence deja la,
     a cote du titre, il n'a rien au-dessus de lui pour le faire remonter : il
     s'accroche des le premier pixel de defilement. C'est ce qui manquait
     quand l'en-tete etait au-dessus de lui plutot qu'a cote. */
  .plan { display: flex; gap: 16px; align-items: flex-start;
          max-width: 1180px; margin: 0 auto; padding: 12px;
          box-sizing: border-box; }

  /* **Centre sur la hauteur de la fenetre, et immobile.** `top: 50%` accroche
     le panneau au milieu, la translation le recentre sur cette ligne plutot
     que de l'y faire commencer. `sticky` plutot que `fixed` : l'element reste
     dans le flux, et sa colonne garde donc sa largeur -- en `fixed`, le
     tableau passait dessous. */
  .cote { position: sticky; top: 50%; transform: translateY(-50%);
          flex: 0 0 auto; max-width: 340px;
          display: flex; flex-direction: column; gap: 10px; }

  /* L'en-tete d'explication defile avec le tableau : elle est dans la meme
     colonne que lui. */
  .defilant { flex: 1 1 auto; min-width: 0; }
  /* Deux colonnes : les quatre zones a gauche, les quatre saisons a droite. */
  .choix { display: flex; gap: 8px; align-items: flex-start; }
  .pile { display: flex; flex-direction: column; gap: 6px; }
  .pile button { text-align: left; white-space: nowrap; }
  #bloc-nom { color: var(--faible); font-size: .9rem; }
  #bloc-nom input { width: 100%; box-sizing: border-box; margin-top: 4px; }
  .cote #lecture { margin: 0; font-size: .85rem; }
  button {
    background: var(--surface); color: var(--texte); cursor: pointer;
    border: 1px solid #24343a; border-radius: 7px; padding: 7px 13px;
    font: inherit;
  }
  button:hover { border-color: var(--sarcelle); }
  button[aria-pressed="true"] {
    background: var(--sarcelle); color: #08120f; border-color: var(--sarcelle);
    font-weight: 600;
  }
  .compte { color: var(--faible); font-size: .9rem; }

  /* Le tableau deborde volontiers en largeur : il defile seul de ce cote-la
     aussi, sans pousser le reste. */
  .cadre { overflow-x: auto; }

  /* Sous mille pixels, deux panneaux cote a cote ne tiennent plus : le
     panneau repasse au-dessus du tableau, en ligne, comme avant. */
  @media (max-width: 1000px) {
    .plan { display: block; }
    .cote { position: static; transform: none; max-width: none;
            flex-direction: row;
            flex-wrap: wrap; align-items: center; margin-bottom: 12px; }
    .choix { flex-wrap: wrap; }
    .pile { flex-direction: row; flex-wrap: wrap; }
    .pile button { text-align: center; }
    #bloc-nom input { width: auto; }
  }
  /* Largeurs posees : laissee libre, la colonne des noms s'etirait sur la
     moitie de l'ecran et les quatre conditions se serraient a droite. */
  table { border-collapse: collapse; width: auto; margin: 0 auto; }
  th, td { border: 1px solid #24343a; padding: 4px 6px; text-align: center; }
  /* **Les bordures d'un en-tete collant s'en vont.** Avec border-collapse,
     elles appartiennent a la grille et non aux cellules : elles defilent donc
     avec le tableau et l'en-tete se retrouve nu, colonnes comprises. Une ombre
     interieure les redessine, et elle, elle colle avec lui. */
  thead th { position: sticky; top: 0; background: var(--surface); z-index: 2;
             border-color: transparent;
             box-shadow: inset 0 0 0 1px #24343a, 0 2px 4px rgba(0,0,0,.45); }
  thead .cond { font-weight: 600; color: var(--clair); white-space: nowrap;
                width: 108px; }
  thead .plage { display: block; font-weight: 400; font-size: .75rem;
                 color: var(--faible); white-space: nowrap; }
  /* Le fond de la ligne de famille est plus clair que la couleur des traits :
     les separations de colonnes y disparaissaient, et l'oeil perdait la
     colonne qu'il suivait en descendant. On les eclaircit juste assez. */
  /* **L'embleme ne compte pas dans le centrage.** Vingt-deux pixels de
     large, cinq de marge a droite, et vingt-sept de marge negative a gauche :
     sa largeur totale est donc nulle, et le centrage ne voit que le nom. Sans
     cela, le nom se decalait vers la droite de la moitie de l'icone -- ce
     qu'on voyait tout de suite en comparant deux familles. */
  .famille .embleme { width: 22px; height: 22px; vertical-align: -5px;
                      margin-right: 5px; margin-left: -27px; }
  /* Le nom de la famille et son embleme sont centres ensemble sur leurs deux
     colonnes. Ils etaient alignes a gauche : le nom se trouvait alors pousse
     d'une largeur d'icone, et le passer devant l'image l'a fait sauter contre
     la bordure. Le centrage regle les deux. */
  .famille th { background: #1d2b30; color: var(--or); text-align: center;
                letter-spacing: .02em; border-color: #3d5560; }
  .famille .vide { background: #1d2b30; border-color: #3d5560; }
  .matiere { text-align: center; white-space: nowrap; font-weight: 600;
             width: 170px; }
  .qualite { color: var(--faible); font-weight: 400; font-size: .85rem;
             width: 54px; }
  /* Le rappel des conditions sur la ligne de la famille : assez lisible pour
     qu'on s'y repere, assez terne pour ne pas voler la vedette au nom jaune. */
  /* Centres : `.famille th` aligne tout a gauche pour le nom de la famille,
     et les rappels heritaient de cet alignement -- ils flottaient donc au bord
     gauche de colonnes larges de cent huit points, loin de la case visee. */
  .famille .rappel .plage { display: block; font-size: .68rem; opacity: .7; }
  .famille .rappel { font-size: .75rem; font-weight: 400; color: var(--clair);
                     letter-spacing: .02em; text-align: center; }
  .q-supp .qualite { color: var(--or); }

  /* **Chaque case dessine son propre contour.** Les bordures fusionnees d'un
     tableau sont partagees entre voisines : a zoom fractionnaire, un trait
     d'un pixel s'arrondit parfois a zero et la ligne disparait sur toute une
     rangee. Une ombre interieure, elle, appartient a la cellule seule. Les
     deux se superposent exactement a cent pour cent -- on ne voit rien de
     plus ; c'est aux autres echelles qu'elle rattrape. */
  .case { cursor: pointer; height: 26px; font-weight: 700; user-select: none;
          box-shadow: inset 0 0 0 1px #24343a; }
  .case:hover { background: #1d2b30; }
  /* **La case cochee garde ses bords.** Son fond vert est plus clair que la
     couleur des traits : la bordure grise s'y noyait, et la colonne semblait
     se rompre a chaque croix. Un contour vert la redessine par-dessus, et il
     ne depend pas de la grille du tableau. */
  .case[data-v="x"] { color: var(--oui); background: rgba(75,191,114,.13);
                      box-shadow: inset 0 0 0 1px rgba(75,191,114,.5); }
  /* Meme soin pour le tiret, dont le fond ne change pas mais qui doit se lire
     comme une reponse et non comme une case oubliee. */
  .case[data-v="-"] { box-shadow: inset 0 0 0 1px rgba(150,160,158,.28); }
  .case[data-v="x"]::after { content: "x"; }
  .case[data-v="-"] { color: var(--non); }
  .case[data-v="-"]::after { content: "\\2212"; }
  /* **L'orange, c'est ce qu'on n'a pas vu soi-meme.** Il vient des landmarks
     des foreuses, de la cartographie du tutoriel ou de Ballistic Mystix. Un
     clic le confirme et il passe au vert ; deux, et il devient un tiret. */
  .case[data-v="?"] { color: var(--dedu);
                      background: rgba(232,161,58,.10);
                      box-shadow: inset 0 0 0 1px rgba(232,161,58,.5); }
  .case[data-v="?"]::after { content: "x"; }

  #bloc-nom { color: var(--faible); font-size: .9rem; }
  #nom { background: var(--fond); color: var(--texte); font: inherit;
         border: 1px solid #24343a; border-radius: 7px; padding: 6px 8px;
         margin-left: 4px; }
  #lecture { max-width: 900px; margin: 0 auto 10px; color: var(--or); }
  /* En lecture seule, rien ne doit laisser croire qu'un clic fera quelque
     chose : ni main de souris, ni case qui s'allume au survol. */
  .lecture-seule .case { cursor: default; }
  .lecture-seule .case:hover { background: none; }
</style>
</head>
<body>
<!-- Le voile : tant que le relevé n'est pas ouvert, la grille reste vide
     derrière. Elle ne contient aucune croix, donc rien ne fuit. -->
<div id="voile" hidden>
  <form id="porte">
    <h2>Relevé de la guilde</h2>
    <p>Le relevé des Primes n'est pas public. Demande le mot de passe à un
       officier de <b>La Lune Éternelle</b>.</p>
    <p id="rappel-clef" hidden>Ta clef d'écriture est reconnue : une fois
       entrée, tu pourras cocher.</p>
    <input type="password" id="mdp" autocomplete="current-password"
           placeholder="mot de passe" required>
    <button type="submit">Entrer</button>
    <span id="refus"></span>
  </form>
</div>

<!-- L'en-tete coiffe les deux colonnes et defile avec la page. Le panneau,
     lui, est accroche au milieu de la fenetre : il ne remonte donc pas avec
     elle, contrairement a un panneau accroche en haut, qui devait attendre
     que l'en-tete soit passee. -->
<header>
  <h1>Relevé de forage des Primes</h1>
  <p>Quand on fore une source dans les Primes, on coche ici. Un clic&nbsp;:
     <b style="color:var(--oui)">x</b> ça sort, <b style="color:var(--non)">−</b>
     ça ne sort pas, un clic de plus efface. Utilisez une stanza précise —
     suprême seulement, ou excellent seulement, ou choix seulement — et lisez le
     message du jeu&nbsp;: <i>pas à cette saison</i>, <i>vidé</i>,
     <i>mauvaises conditions climatiques</i>.</p>
  <p>Une croix <b style="color:var(--dedu)">orange</b> vient d'une autre
     source — carnets de foreuses, tutoriel, Ballistic Mystix — et n'a pas été
     vue en jeu. Un clic la confirme et elle passe au vert.</p>
  <p>Les conditions climatiques se lisent sur
     <a href="http://ballisticmystix.net/?p=atys_calendar#">ballistic mystix</a>
     ou dans ZyRoom. Vérifiez l'heure avant de corriger une case&nbsp;: il y a
     parfois plusieurs heures de décalage.</p>
</header>

<div class="plan">

<aside class="cote">
  <div class="choix">
    <div class="pile">__ZONES__</div>
    <div class="pile">__ONGLETS__</div>
  </div>
  <label id="bloc-nom">Ton nom&nbsp;:
    <input id="nom" maxlength="24" size="12" placeholder="Xiom" spellcheck="false">
  </label>
  <span class="compte" id="compte">chargement…</span>
  <p id="lecture" hidden>Lecture seule&nbsp;: demande le lien de saisie dans
     le canal de guilde pour pouvoir cocher.</p>
</aside>

<div class="defilant">



<div class="cadre">
  <table>
    <thead>
      <tr>
        <th colspan="2" id="titre-saison"></th>
        __ENTETES__
      </tr>
    </thead>
    <tbody id="corps">__GRILLE__</tbody>
  </table>
</div>

</div>
</div>

<style>
  #voile {
    position: fixed; inset: 0; z-index: 50;
    background: #10171a;
    display: flex; align-items: center; justify-content: center;
    padding: 16px;
  }
  /* **Sans cette ligne, le voile ne se ferme jamais.** L'attribut `hidden`
     agit par la regle `[hidden] { display: none }` de la feuille du
     navigateur, de specificite 0-1-0 ; `#voile { display: flex }` vaut
     1-0-0 et l'emporte. Le voile restait donc affiche par-dessus un tableau
     pourtant charge : la clef ouvrait bien, le mot de passe etait accepte,
     et rien ne bougeait a l'ecran. Il a fallu deux soirees pour le voir,
     parce que les essais lisaient la propriete `.hidden` -- vraie -- au lieu
     de regarder ce qui etait peint. */
  #voile[hidden] { display: none; }
  #porte {
    max-width: 22rem; width: 100%;
    display: flex; flex-direction: column; gap: .7rem;
  }
  #porte h2 { margin: 0; color: #d8b35a; font-size: 1.3rem; }
  #porte p { margin: 0; color: #9fb0ad; line-height: 1.5; font-size: .95rem; }
  #porte p#rappel-clef { color: #6fae9c; }
  /* Meme piege que pour #voile : une regle d'identifiant ecrase le
     `[hidden] { display: none }` du navigateur. */
  #porte p[hidden] { display: none; }
  #porte input, #porte button {
    font: inherit; padding: .6rem .8rem; border-radius: 6px;
    border: 1px solid #2d3f42; background: #16232a; color: #e6efec;
  }
  #porte button {
    background: #2f5d52; border-color: #3f7a68; cursor: pointer;
    font-weight: 600;
  }
  #porte button:hover { background: #3f7a68; }
  #refus { color: #d97a6c; min-height: 1.2em; font-size: .9rem; }
</style>
<script>
  "use strict";
  const SAISONS = __SAISONS__;
  const ZONES = __LISTE_ZONES__;
  // La clef de saisie voyage dans l'adresse : sans elle, la page se lit et ne
  // se coche pas. C'est le lien qu'on colle dans le canal de guilde.
  const CLE = new URLSearchParams(location.search).get("k") || "";

  let saison = 0;
  let zone = 0;
  let cases = {};              // "saison|matiere|qualite|condition" -> {v, qui}
  let enVol = 0;

  const corps = document.getElementById("corps");
  const compte = document.getElementById("compte");
  const nom = document.getElementById("nom");

  if (!CLE) {
    document.getElementById("lecture").hidden = false;
    document.getElementById("bloc-nom").hidden = true;
    document.body.classList.add("lecture-seule");
  }
  try { nom.value = localStorage.getItem("forage-nom") || ""; } catch (e) {}
  nom.addEventListener("change", () => {
    try { localStorage.setItem("forage-nom", nom.value.trim()); } catch (e) {}
  });

  function cle(td) {
    return ZONES[zone] + "|" + SAISONS[saison] + "|" + td.dataset.cle;
  }

  function peindre() {
    document.getElementById("titre-saison").textContent =
      ZONES[zone] + " — " + SAISONS[saison];
    for (const td of corps.querySelectorAll(".case")) {
      const c = cases[cle(td)];
      if (c) {
        td.dataset.v = c.v;
        // Qui a coche, et quand : sur un tableau rempli a plusieurs sur des
        // mois, c'est a quoi on se raccroche quand deux releves divergent.
        td.title = (c.qui || "quelqu'un") + (c.quand ? " — " + c.quand.slice(0, 10) : "");
      } else {
        delete td.dataset.v;
        td.removeAttribute("title");
      }
    }
    const n = Object.keys(cases).length;
    compte.textContent = n + " case" + (n > 1 ? "s" : "") + " cochée"
                         + (n > 1 ? "s" : "") + (CLE ? "" : " · lecture seule");
  }

  // Le jeton de lecture, garde en second recours : certains navigateurs
  // n'ecrivent pas les cookies (effacement a la fermeture, navigation privee),
  // et la connexion reussissait sans que la lecture suivante passe.
  function jeton() {
    try { return localStorage.getItem("forage") || ""; } catch (e) { return ""; }
  }
  function garderJeton(v) {
    try { localStorage.setItem("forage", v); } catch (e) { /* tant pis */ }
  }
  function entetes(base) {
    const h = Object.assign({}, base || {});
    const j = jeton();
    if (j) h["X-Forage"] = j;
    return h;
  }

  const voile = document.getElementById("voile");
  if (CLE) {
    const rappel = document.getElementById("rappel-clef");
    if (rappel) { rappel.hidden = false; }
  }
  const porte = document.getElementById("porte");
  const refus = document.getElementById("refus");

  async function charger() {
    try {
      // La clef ne sert plus a entrer : elle donne le droit d'ecrire, et
      // le mot de passe ouvre la porte -- sur les deux adresses.
      const r = await fetch("releve.php", { cache: "no-store",
                                            headers: entetes() });
      if (r.status === 401) {
        voile.hidden = false;
        document.getElementById("mdp").focus();
        return;
      }
      const d = await r.json();
      cases = d.cases || {};
      voile.hidden = true;
      peindre();
    } catch (e) {
      compte.textContent = "relevé injoignable";
    }
  }

  porte.addEventListener("submit", async (e) => {
    e.preventDefault();
    const champ = document.getElementById("mdp");
    refus.textContent = "";
    const bouton = porte.querySelector("button");
    bouton.disabled = true;
    bouton.textContent = "…";
    try {
      const r = await fetch("releve.php", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "entrer", mdp: champ.value })
      });
      if (!r.ok) {
        refus.textContent = "Mot de passe refusé.";
        champ.select();
        return;
      }
      const d = await r.json().catch(() => ({}));
      if (d.jeton) {
        garderJeton(d.jeton);
      }
      await charger();
      if (!voile.hidden) {
        refus.textContent =
          "Mot de passe accepté, mais ce navigateur n'en garde pas la trace.";
      }
    } catch (err) {
      refus.textContent = "Serveur injoignable.";
    } finally {
      bouton.disabled = false;
      bouton.textContent = "Entrer";
    }
  });

  async function envoyer(k, v) {
    enVol++;
    try {
      const r = await fetch("releve.php", {
        method: "POST",
        headers: entetes({ "Content-Type": "application/json" }),
        body: JSON.stringify({ cle: CLE, case: k, valeur: v,
                               foreuse: nom.value.trim() })
      });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        throw new Error(d.erreur || r.status);
      }
      return true;
    } catch (e) {
      compte.textContent = "refusé : " + e.message;
      return false;
    } finally {
      enVol--;
    }
  }

  corps.addEventListener("click", async (e) => {
    if (!CLE) return;
    const td = e.target.closest(".case");
    if (!td) return;
    const k = cle(td);
    const avant = cases[k];
    // L'orange se confirme d'un clic : il devient vert. Puis tiret, puis vide.
    const suite = { undefined: "x", "?": "x", "x": "-", "-": undefined };
    const v = suite[avant ? avant.v : undefined];
    // On peint d'abord et on demande ensuite : le clic doit repondre tout de
    // suite. Si le serveur refuse, on remet ce qui etait la.
    if (v) {
      cases[k] = { v: v, qui: nom.value.trim(), quand: new Date().toISOString() };
    } else {
      delete cases[k];
    }
    peindre();
    if (!await envoyer(k, v || "")) {
      if (avant) { cases[k] = avant; } else { delete cases[k]; }
      peindre();
    }
  });

  // Les deux rangees d'onglets marchent pareil : on change l'indice, on
  // rallume le bouton choisi, et la meme grille se repeint. Seize tableaux --
  // quatre zones par quatre saisons -- et une seule grille dessinee.
  for (const [attribut, poser] of [["data-saison", (n) => { saison = n; }],
                                   ["data-zone", (n) => { zone = n; }]]) {
    for (const b of document.querySelectorAll("[" + attribut + "]")) {
      b.addEventListener("click", () => {
        poser(Number(b.dataset[attribut === "data-zone" ? "zone" : "saison"]));
        for (const a of document.querySelectorAll("[" + attribut + "]")) {
          a.setAttribute("aria-pressed", a === b ? "true" : "false");
        }
        peindre();
      });
    }
  }

  // On relit regulierement : deux foreuses sur le meme creneau doivent voir
  // les croix l'une de l'autre sans recharger la page. Jamais pendant qu'une
  // ecriture est en vol, sinon elle reviendrait effacee.
  setInterval(() => { if (enVol === 0) charger(); }, 45000);
  // Peindre d'abord : sans cela, le titre du tableau reste vide tant que le
  // serveur n'a pas repondu -- et vide pour toujours s'il ne repond jamais.
  peindre();
  charger();
</script>
</body>
</html>
"""


def _liste_php(elements) -> str:
    """Une liste PHP littérale, guillemets simples échappés."""
    return "[" + ", ".join("'" + str(e).replace("\\", "\\\\")
                           .replace("'", "\\'") + "'" for e in elements) + "]"


def main() -> int:
    familles = catalogue()
    matieres = [m.replace("²", "").strip()
                for _f, ms in familles for m in ms]
    entetes = "\n        ".join(
        f'<th class="cond">{fr}<span class="plage">{court} · {plage}</span></th>'
        for fr, court, plage in CONDITIONS)
    onglets = "\n  ".join(
        f'<button data-saison="{i}" aria-pressed="{"true" if i == 0 else "false"}">'
        f'{s}</button>' for i, s in enumerate(SAISONS))
    zones = "\n  ".join(
        f'<button data-zone="{i}" aria-pressed="{"true" if i == 0 else "false"}">'
        f'{z}</button>' for i, z in enumerate(ZONES))
    page = (GABARIT
            .replace("__ONGLETS__", onglets)
            .replace("__ZONES__", zones)
            .replace("__LISTE_ZONES__", repr(list(ZONES)).replace("'", '"'))
            .replace("__ENTETES__", entetes)
            .replace("__GRILLE__", grille(familles))
            .replace("__SAISONS__", repr(list(SAISONS)).replace("'", '"')))
    php = (PHP
           .replace("__CLE__", clef())
           .replace("__EMPREINTE__", empreinte_mot_de_passe())
           .replace("__SEL__", sel())
           .replace("__ZONES__", _liste_php(ZONES))
           .replace("__SAISONS__", _liste_php(SAISONS))
           .replace("__QUALITES__", _liste_php(QUALITES))
           # Le nom court, et non le francais : c'est lui que `grille()` met
           # dans data-cle, donc lui que la page enverra.
           .replace("__CONDITIONS__", _liste_php(c[1] for c in CONDITIONS))
           .replace("__MATIERES__", _liste_php(matieres)))

    # Les deux moitieses doivent nommer les cases pareil. L'ecart precedent --
    # la page envoyait « Worst », le serveur attendait « Execrable » -- ne se
    # voyait qu'a l'usage, et sous la forme d'un refus sans explication.
    attendues = {c[1] for c in CONDITIONS}
    ecrites = set(re.findall(r'data-cle="[^"]*\|([^"|]+)"', page))
    if ecrites != attendues:
        raise SystemExit(f"conditions : la page écrit {sorted(ecrites)}, "
                         f"le serveur attend {sorted(attendues)}")

    dossier = os.path.dirname(CIBLE)
    os.makedirs(dossier, exist_ok=True)
    ecrits = []
    for nom, contenu in (("index.html", page), ("releve.php", php),
                         (".htaccess", HTACCESS)):
        chemin = os.path.join(dossier, nom)
        with open(chemin, "w", encoding="utf-8") as fh:
            fh.write(contenu)
        ecrits.append((nom, len(contenu)))

    par_tableau = len(matieres) * len(QUALITES) * len(CONDITIONS)
    print(f"{len(familles)} familles, {len(matieres)} matières, "
          f"{par_tableau} cases par tableau — {len(ZONES)} zones × "
          f"{len(SAISONS)} saisons = "
          f"{par_tableau * len(ZONES) * len(SAISONS)} au total")
    for nom, poids in ecrits:
        print(f"  {nom:12s} {poids // 1024 or 1:3d} Kio")
    print(f"→ {dossier}")
    print("clef d'écriture : voir " + CLE_FICHIER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
